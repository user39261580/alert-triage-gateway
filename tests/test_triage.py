from unittest.mock import patch

import pytest

from src.models import AlertTriage, TriageRequest
from src.evaluator import score_triage


class TestScoreTriage:
    def test_none_input_returns_zero(self):
        score, valid = score_triage(None)
        assert score == 0.0
        assert valid is False

    @patch("src.evaluator.check_service_exists", return_value=True)
    def test_perfect_triage_scores_one(self, _mock_db):
        triage = AlertTriage(
            service_name="auth-service",
            severity_level="CRITICAL",
            is_database_issue=True,
        )
        score, valid = score_triage(triage)
        assert score == 1.0
        assert valid is True

    @patch("src.evaluator.check_service_exists", return_value=False)
    def test_hallucinated_service_scores_half(self, _mock_db):
        triage = AlertTriage(
            service_name="made-up-service",
            severity_level="LOW",
            is_database_issue=False,
        )
        score, valid = score_triage(triage)
        assert score == 0.5
        assert valid is False

    @patch("src.evaluator.check_service_exists", return_value=True)
    def test_valid_service_all_severities(self, _mock_db):
        for severity in ["LOW", "MEDIUM", "CRITICAL"]:
            triage = AlertTriage(
                service_name="checkout-api",
                severity_level=severity,
                is_database_issue=False,
            )
            score, valid = score_triage(triage)
            assert score == 1.0
            assert valid is True


class TestTriageRequest:
    def test_model_defaults_to_gpt_4o_mini(self):
        req = TriageRequest(raw_log="Connection timeout on auth-service")
        assert req.model == "gpt-4o-mini"

    def test_model_can_be_overridden(self):
        req = TriageRequest(raw_log="Connection timeout on auth-service", model="gpt-5.4-mini")
        assert req.model == "gpt-5.4-mini"


@pytest.mark.integration
class TestTriageEndpoint:
    BASE_URL = "http://localhost:8000/api/v1"

    def test_health_check(self):
        import httpx

        response = httpx.get("http://localhost:8000/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_valid_alert_returns_200_with_trust_score(self):
        import httpx

        payload = {"raw_log": "Connection timeout on auth-service port 5432, severity CRITICAL."}
        response = httpx.post(f"{self.BASE_URL}/triage-alert", json=payload)
        assert response.status_code == 200

        body = response.json()
        assert "trust_score" in body
        assert 0.0 <= body["trust_score"] <= 1.0
        assert "service_valid" in body
        assert body["triage"]["severity_level"] in {"LOW", "MEDIUM", "CRITICAL"}

    def test_short_log_returns_422(self):
        import httpx

        response = httpx.post(f"{self.BASE_URL}/triage-alert", json={"raw_log": "ab"})
        assert response.status_code == 422

    def test_langfuse_trace_id_is_returned(self):
        import httpx

        payload = {"raw_log": "Fatal: user-billing-db unreachable. All payments failing."}
        response = httpx.post(f"{self.BASE_URL}/triage-alert", json=payload)
        assert response.status_code == 200
        assert response.json().get("langfuse_trace_id") is not None
