from typing import Literal

from pydantic import BaseModel, Field


class TriageRequest(BaseModel):
    raw_log: str = Field(
        ...,
        min_length=5,
        max_length=2000,
        description="Raw alert/error log text to triage",
    )
    model: str = Field(
        default="gpt-4o-mini",
        min_length=1,
        max_length=128,
        description="LLM model name used for extraction",
    )


class AlertTriage(BaseModel):
    service_name: str
    severity_level: Literal["LOW", "MEDIUM", "CRITICAL"]
    is_database_issue: bool


class TriageResponse(BaseModel):
    triage: AlertTriage
    trust_score: float
    service_valid: bool
    langfuse_trace_id: str | None = None
