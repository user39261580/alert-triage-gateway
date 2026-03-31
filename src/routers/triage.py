from fastapi import APIRouter, HTTPException
from langfuse import get_client, observe

from src.database import write_triage_log
from src.evaluator import score_triage
from src.llm_client import extract_triage_from_log
from src.models import TriageRequest, TriageResponse

router = APIRouter(prefix="/api/v1", tags=["Triage"])


@router.post("/triage-alert", response_model=TriageResponse)
@observe(name="triage_pipeline")
async def triage_alert(req: TriageRequest) -> TriageResponse:
    """Run extraction, evaluate trust, log result, and return response."""
    langfuse = get_client()

    triage = extract_triage_from_log(req.raw_log)
    if triage is None:
        raise HTTPException(status_code=422, detail="LLM failed to produce valid JSON")

    trust_score, service_valid = score_triage(triage)

    trace_id = langfuse.get_current_trace_id()
    if trace_id:
        langfuse.score(
            trace_id=trace_id,
            name="trust_score",
            value=trust_score,
            comment=f"service_valid={service_valid}",
        )

    write_triage_log(req.raw_log, triage, trust_score, trace_id)

    return TriageResponse(
        triage=triage,
        trust_score=trust_score,
        service_valid=service_valid,
        langfuse_trace_id=trace_id,
    )
