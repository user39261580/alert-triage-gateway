from fastapi import APIRouter, HTTPException
from langfuse import get_client, observe

from src.database import write_triage_log
from src.evaluator import score_triage
from src.llm_client import extract_triage_from_log
from src.models import TriageRequest, TriageResponse

router = APIRouter(prefix="/api/v1", tags=["Triage"])


def _score_current_trace(langfuse_client, trust_score: float, service_valid: bool) -> None:
    """Record trust_score on the root trace for dashboard filtering."""
    comment = f"service_valid={service_valid}"

    if hasattr(langfuse_client, "score_current_trace"):
        langfuse_client.score_current_trace(
            name="trust_score",
            value=trust_score,
            comment=comment,
            metadata={"service_valid": service_valid},
        )
        return

    trace_id = langfuse_client.get_current_trace_id()
    if trace_id and hasattr(langfuse_client, "score"):
        langfuse_client.score(
            trace_id=trace_id,
            name="trust_score",
            value=trust_score,
            comment=comment,
        )


@router.post("/triage-alert", response_model=TriageResponse)
@observe(name="triage_pipeline")
async def triage_alert(req: TriageRequest) -> TriageResponse:
    """Run extraction, evaluate trust, log result, and return response."""
    langfuse = get_client()

    if hasattr(langfuse, "update_current_span"):
        langfuse.update_current_span(metadata={"requested_model": req.model})

    triage = extract_triage_from_log(req.raw_log, model=req.model)
    if triage is None:
        raise HTTPException(status_code=422, detail="LLM failed to produce valid JSON")

    trust_score, service_valid = score_triage(triage)

    _score_current_trace(langfuse, trust_score, service_valid)

    trace_id = langfuse.get_current_trace_id()

    write_triage_log(req.raw_log, triage, trust_score, trace_id)

    return TriageResponse(
        triage=triage,
        trust_score=trust_score,
        service_valid=service_valid,
        langfuse_trace_id=trace_id,
    )
