import logging
import time

from fastapi import APIRouter, HTTPException
from langfuse import get_client, observe

from src.database import write_triage_log
from src.evaluator import score_triage
from src.llm_client import extract_triage_from_log
from src.models import TriageRequest, TriageResponse
from src.telemetry import (
    record_triage_metrics,
    record_triage_request_finished,
    record_triage_request_started,
)

router = APIRouter(prefix="/api/v1", tags=["Triage"])
logger = logging.getLogger("alert-triage-gateway.triage")


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
    started_at = time.perf_counter()
    record_triage_request_started(model=req.model)
    langfuse = get_client()
    logger.info("triage_request_started", extra={"model": req.model})

    try:
        if hasattr(langfuse, "update_current_span"):
            langfuse.update_current_span(metadata={"requested_model": req.model})

        triage = extract_triage_from_log(req.raw_log, model=req.model)
        if triage is None:
            latency_ms = (time.perf_counter() - started_at) * 1000
            record_triage_metrics(model=req.model, status="unprocessable", latency_ms=latency_ms)
            logger.warning(
                "triage_request_unprocessable",
                extra={"model": req.model, "latency_ms": round(latency_ms, 2)},
            )
            raise HTTPException(status_code=422, detail="LLM failed to produce valid JSON")

        trust_score, service_valid = score_triage(triage)

        _score_current_trace(langfuse, trust_score, service_valid)

        trace_id = langfuse.get_current_trace_id()

        write_triage_log(req.raw_log, triage, trust_score, trace_id)

        latency_ms = (time.perf_counter() - started_at) * 1000
        record_triage_metrics(
            model=req.model,
            status="ok",
            latency_ms=latency_ms,
            trust_score=trust_score,
        )
        logger.info(
            "triage_request_completed",
            extra={
                "model": req.model,
                "latency_ms": round(latency_ms, 2),
                "trust_score": trust_score,
                "service_valid": service_valid,
                "trace_id": trace_id,
            },
        )

        return TriageResponse(
            triage=triage,
            trust_score=trust_score,
            service_valid=service_valid,
            langfuse_trace_id=trace_id,
        )
    except HTTPException:
        raise
    except Exception:
        latency_ms = (time.perf_counter() - started_at) * 1000
        record_triage_metrics(model=req.model, status="error", latency_ms=latency_ms)
        logger.exception(
            "triage_request_failed",
            extra={"model": req.model, "latency_ms": round(latency_ms, 2)},
        )
        raise
    finally:
        record_triage_request_finished(model=req.model)
