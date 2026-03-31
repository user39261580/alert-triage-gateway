from langfuse import observe

from src.database import check_service_exists
from src.models import AlertTriage

VALID_SEVERITIES = {"LOW", "MEDIUM", "CRITICAL"}


@observe(name="evaluation_scorer")
def score_triage(triage: AlertTriage | None) -> tuple[float, bool]:
    """Score the triage result and verify service_name against PostgreSQL."""
    if triage is None:
        return 0.0, False

    score = 0.2

    if triage.severity_level in VALID_SEVERITIES:
        score += 0.3

    service_valid = check_service_exists(triage.service_name)
    if service_valid:
        score += 0.5

    return round(score, 2), service_valid
