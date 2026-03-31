# Dual-Observable Alert Triage Gateway — Full Implementation Plan

> Updated to Langfuse Python SDK v3 (GA June 2025), HyperDX image updated post-ClickHouse acquisition (March 2025), and Docker Compose simplified to two instead of three data-store services.

---

## Project Overview

This project builds a **production-grade alert triage API** that ingests raw server error strings, uses an LLM to extract structured data, and immediately evaluates the LLM's output for hallucinations — all while being fully observable at both the **system level** (HyperDX/OTel) and the **AI level** (Langfuse), with PostgreSQL as ground-truth storage.

---

## What Changed From the Original Plan (Fix Summary)

| # | Issue | Fix Applied |
|---|---|---|
| B1 | `choices[^1_0]` Markdown artifact breaks Python | Changed to `choices[0]` |
| B2 | Langfuse client never initialized; `langfuse.decorators` is v2 API | Updated all imports to Langfuse Python SDK v3: `from langfuse import observe, get_client` |
| B3 | No SQLAlchemy version pin; `with SessionLocal()` requires ≥2.0 | Pinned `sqlalchemy>=2.0` in `requirements.txt` |
| F4 | `trace_id=None` hardcoded; trace cross-linking never worked | Capture real ID via `get_client().get_current_trace_id()` in root span |
| F5 | `score_current_observation` attached score to child span, not root trace | Moved scoring to root `triage_pipeline` span via `langfuse.score(trace_id=...)` |
| M6 | No Docker `healthcheck:` blocks despite docs saying to watch for "healthy" | Added `healthcheck` to postgres; `depends_on` uses `condition: service_healthy` |
| M7 | Langfuse batch sender may not flush before process exits | Replaced deprecated `on_event` with `lifespan` context manager + `get_client().flush()` |
| M8 | `test_triage.py` listed but never written | Added complete test file with unit + integration tests |
| M9 | `docker.hyperdx.io` registry URL is stale; HyperDX acquired by ClickHouse (March 2025) | Updated to `hyperdx/hyperdx-all-in-one:2-nightly` (Docker Hub) |
| M10 | Separate ClickHouse service was redundant | Removed: the HyperDX all-in-one image bundles ClickHouse internally |

---

## Repository Structure

```
alert-triage-gateway/
├── docker-compose.yml          # All infra services
├── .env                        # Secrets (never commit)
├── .env.example                # Template for secrets
├── schema.sql                  # PostgreSQL seed script
├── requirements.txt
├── src/
│   ├── main.py                 # FastAPI entrypoint + OTel setup + lifespan
│   ├── models.py               # Pydantic schemas
│   ├── database.py             # PostgreSQL connection pool
│   ├── llm_client.py           # LLM call + Langfuse tracing (v3 SDK)
│   ├── evaluator.py            # Evaluation scoring logic
│   └── routers/
│       └── triage.py           # POST /triage-alert endpoint
├── tests/
│   ├── test_triage.py          # Unit + integration tests
│   └── sample_payloads.json    # Test inputs for manual curl
├── screenshots/                # HyperDX + Langfuse screenshots for README
└── README.md
```

---

## Phase 1: Preparing Phase (Infrastructure Setup)

### Step 1.1 — Write `docker-compose.yml`

> **What changed:** Removed the separate `clickhouse` service — `hyperdx-all-in-one:2-nightly` bundles its own ClickHouse internally after the ClickHouse acquisition of HyperDX in March 2025. The `LANGFUSE_CLICKHOUSE_*` vars are omitted; Langfuse runs on PostgreSQL only for this demo. Added `healthcheck` on postgres so dependent services wait for it to be ready.

```yaml
version: "3.9"

services:
  postgres:
    image: postgres:15-alpine
    container_name: infra_postgres
    environment:
      POSTGRES_DB: infra_ops
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: secret
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./schema.sql:/docker-entrypoint-initdb.d/schema.sql
    # FIX M6: healthcheck lets dependent services wait for postgres to accept connections
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U admin -d infra_ops"]
      interval: 5s
      timeout: 5s
      retries: 10
      start_period: 10s

  hyperdx:
    # FIX M9: docker.hyperdx.io registry is stale — image now lives on Docker Hub.
    # hyperdx-all-in-one bundles ClickHouse + OTel collector + HyperDX UI in one container.
    image: hyperdx/hyperdx-all-in-one:2-nightly
    container_name: infra_hyperdx
    ports:
      - "8080:8080"   # HyperDX UI
      - "4317:4317"   # OTel gRPC ingest
      - "4318:4318"   # OTel HTTP ingest
    environment:
      # Set a fixed API key so you can configure sources in the UI
      __HDX_API_KEY: local-dev-key
    # No depends_on needed — HyperDX is self-contained

  langfuse:
    image: langfuse/langfuse:2
    container_name: infra_langfuse
    environment:
      DATABASE_URL: postgresql://admin:secret@postgres:5432/infra_ops
      NEXTAUTH_SECRET: langfuse_nextauth_secret_changeme
      NEXTAUTH_URL: http://localhost:3000
      SALT: langfuse_salt_changeme
      # Required in Langfuse 2.x+ — must be exactly 32 hex characters (128 bits)
      ENCRYPTION_KEY: 0000000000000000000000000000000000000000000000000000000000000000
    ports:
      - "3000:3000"
    depends_on:
      postgres:
        # FIX M6: only start Langfuse once postgres is confirmed healthy
        condition: service_healthy

volumes:
  postgres_data:
```

**Validation checkpoint:** Run `docker compose up -d`. Open `http://localhost:8080` (HyperDX) and `http://localhost:3000` (Langfuse). The postgres container should show `healthy` in `docker compose ps`. If Langfuse shows a login screen, the infra is ready.

---

### Step 1.2 — Write `schema.sql` (Auto-seeded via Docker)

```sql
-- Ground truth for hallucination detection
CREATE TABLE IF NOT EXISTS valid_services (
    id           SERIAL PRIMARY KEY,
    service_name VARCHAR(255) UNIQUE NOT NULL,
    team_owner   VARCHAR(255) NOT NULL,
    tier         VARCHAR(50)  NOT NULL DEFAULT 'standard'  -- 'critical' | 'standard'
);

INSERT INTO valid_services (service_name, team_owner, tier) VALUES
    ('user-billing-db',  'payments-team',  'critical'),
    ('auth-service',     'identity-team',  'critical'),
    ('checkout-api',     'commerce-team',  'critical'),
    ('notification-svc', 'comms-team',     'standard'),
    ('image-resizer',    'media-team',     'standard')
ON CONFLICT DO NOTHING;

-- Audit log for every triage result
CREATE TABLE IF NOT EXISTS triage_log (
    id                SERIAL PRIMARY KEY,
    raw_input         TEXT          NOT NULL,
    service_name      VARCHAR(255),
    severity_level    VARCHAR(50),
    is_db_issue       BOOLEAN,
    trust_score       FLOAT,
    langfuse_trace_id VARCHAR(255),   -- cross-link to Langfuse UI
    created_at        TIMESTAMPTZ    DEFAULT NOW()
);
```

---

### Step 1.3 — Python Environment Setup

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install \
  fastapi "uvicorn[standard]" \
  "psycopg2-binary" "sqlalchemy>=2.0" \
  pydantic pydantic-settings \
  openai "langfuse>=3.0" \
  opentelemetry-sdk \
  opentelemetry-exporter-otlp-proto-http \
  opentelemetry-instrumentation-fastapi \
  opentelemetry-instrumentation-psycopg2 \
  httpx pytest pytest-asyncio

pip freeze > requirements.txt
```

> **What changed (B3):** Added `sqlalchemy>=2.0` pin — `with SessionLocal() as session:` only works as a context manager in SQLAlchemy 2.x. Also updated `langfuse>=3.0` since v3 is now GA (June 2025) and uses a different import path.

---

### Step 1.4 — `.env` and `.env.example`

```env
# .env (never commit this file)
OPENAI_API_KEY=sk-...
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=http://localhost:3000

DATABASE_URL=postgresql://admin:secret@localhost:5432/infra_ops

OTEL_SERVICE_NAME=alert-triage-gateway
# OTel SDK reads OTEL_EXPORTER_OTLP_ENDPOINT and appends /v1/traces automatically
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
```

---

## Phase 2: Real-Working Phase (Code Implementation)

### Step 2.1 — `src/models.py` — Pydantic Schemas

```python
from pydantic import BaseModel, Field
from typing import Literal, Optional


class TriageRequest(BaseModel):
    raw_log: str = Field(
        ..., min_length=5, max_length=2000,
        example="Timeout on auth-service port 5432, retried 3x"
    )


class AlertTriage(BaseModel):
    service_name: str
    severity_level: Literal["LOW", "MEDIUM", "CRITICAL"]
    is_database_issue: bool


class TriageResponse(BaseModel):
    triage: AlertTriage
    trust_score: float           # 0.0 – 1.0
    service_valid: bool          # Was service_name found in DB?
    langfuse_trace_id: Optional[str] = None
```

---

### Step 2.2 — `src/database.py` — Connection Pool

> **What changed (B3):** Added `sqlalchemy>=2.0` context manager pattern. `with SessionLocal() as session:` is natively supported in SQLAlchemy 2.0. No `contextlib` wrapper needed.

```python
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)


def check_service_exists(service_name: str) -> bool:
    """Returns True if service_name is in the valid_services table."""
    with SessionLocal() as session:
        result = session.execute(
            text("SELECT 1 FROM valid_services WHERE service_name = :name"),
            {"name": service_name}
        ).fetchone()
        return result is not None


def write_triage_log(
    raw_input: str,
    triage,
    score: float,
    trace_id: str | None
) -> None:
    with SessionLocal() as session:
        session.execute(text("""
            INSERT INTO triage_log
                (raw_input, service_name, severity_level, is_db_issue, trust_score, langfuse_trace_id)
            VALUES
                (:raw, :svc, :sev, :db, :score, :trace)
        """), {
            "raw":   raw_input,
            "svc":   triage.service_name,
            "sev":   triage.severity_level,
            "db":    triage.is_database_issue,
            "score": score,
            "trace": trace_id,
        })
        session.commit()
```

---

### Step 2.3 — `src/llm_client.py` — LLM Call with Langfuse Tracing

> **What changed (B1, B2):**
> - `choices[0]` — fixed the `[^1_0]` Markdown artifact that would cause a `SyntaxError`.
> - Import path updated to Langfuse v3: `from langfuse import observe, get_client` (replaces `langfuse.decorators`).
> - No manual `Langfuse()` instantiation needed — `get_client()` is a singleton that auto-reads env vars.

```python
import json
from openai import OpenAI
# FIX B2: Langfuse v3 SDK — import from top-level package, not langfuse.decorators
from langfuse import observe, get_client
from src.models import AlertTriage

openai_client = OpenAI()

SYSTEM_PROMPT = """
You are an infrastructure reliability assistant.
Extract information from the raw server log and output ONLY valid JSON.
The JSON must match this exact schema:
{
  "service_name": "<string — the exact microservice name>",
  "severity_level": "<LOW | MEDIUM | CRITICAL>",
  "is_database_issue": <true | false>
}
Do not include any explanation. Output raw JSON only.
"""


@observe(name="llm_extraction")
def extract_triage_from_log(raw_log: str) -> AlertTriage | None:
    """
    Calls the LLM. The @observe decorator automatically sends the prompt,
    response, and token usage to Langfuse as a child span.
    """
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": f"Log: {raw_log}"},
        ],
        temperature=0,  # Deterministic output is critical for evaluation
        response_format={"type": "json_object"},
    )

    # FIX B1: was choices[^1_0] — Markdown footnote artifact; must be choices[0]
    raw_json = response.choices[0].message.content
    try:
        data = json.loads(raw_json)
        return AlertTriage(**data)
    except Exception:
        return None  # JSON parse failure → trust_score = 0.0
```

---

### Step 2.4 — `src/evaluator.py` — Scoring Logic

> **What changed (F5):** Removed `langfuse_context.score_current_observation(...)` from this file. Scoring at the observation level only reaches the child span, not the root trace. The root-level score is now pushed from `triage.py` using `langfuse.score(trace_id=...)`. This evaluator now only computes and returns the numeric score.

```python
from langfuse import observe
from src.models import AlertTriage
from src.database import check_service_exists

VALID_SEVERITIES = {"LOW", "MEDIUM", "CRITICAL"}


@observe(name="evaluation_scorer")
def score_triage(triage: AlertTriage | None) -> tuple[float, bool]:
    """
    Returns (trust_score, service_valid).

    Score breakdown:
      +0.2  LLM returned parseable JSON (implicitly true if triage is not None)
      +0.3  severity_level is a valid enum value
      +0.5  service_name exists in PostgreSQL valid_services (hallucination check)

    NOTE: Root-trace-level score is pushed from triage.py after this returns,
    using the trace_id captured at the root @observe span.
    """
    if triage is None:
        return 0.0, False

    score = 0.2  # base: JSON parsed successfully

    if triage.severity_level in VALID_SEVERITIES:
        score += 0.3

    service_valid = check_service_exists(triage.service_name)
    if service_valid:
        score += 0.5

    return round(score, 2), service_valid
```

---

### Step 2.5 — `src/main.py` — FastAPI App + OTel Bootstrap

> **What changed (M7):** Replaced the deprecated `@app.on_event("shutdown")` with the modern FastAPI `lifespan` async context manager (recommended since FastAPI 0.93). The `get_client().flush()` call in the shutdown block ensures Langfuse's async batch sender empties its queue before the process exits — critical when you only send 4 payloads in a demo and the buffer may never auto-flush.

```python
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from langfuse import get_client


def _setup_otel() -> None:
    """Bootstrap OpenTelemetry. Must run before the FastAPI app is created."""
    provider = TracerProvider()
    # OTLPSpanExporter reads OTEL_EXPORTER_OTLP_ENDPOINT from env automatically.
    # It appends /v1/traces to the base URL — do not add the path manually.
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)
    Psycopg2Instrumentor().instrument()  # auto-traces all DB queries → visible in HyperDX


_setup_otel()


# FIX M7: lifespan replaces the deprecated @app.on_event("shutdown")
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield  # application runs here
    # Shutdown: flush Langfuse's async batch queue before process exits
    get_client().flush()


app = FastAPI(title="Alert Triage Gateway", version="1.0.0", lifespan=lifespan)
FastAPIInstrumentor.instrument_app(app)  # auto-traces all HTTP requests

from src.routers.triage import router
app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok"}
```

---

### Step 2.6 — `src/routers/triage.py` — The Core Endpoint

> **What changed (F4, F5):**
> - `trace_id` is now captured via `get_client().get_current_trace_id()` **inside** the `@observe`-decorated function so it has access to the live trace context.
> - `langfuse.score(trace_id=..., ...)` pushes the trust score to the **root trace** in Langfuse, not a child span — making it appear in the Langfuse Scores Chart as intended.

```python
from fastapi import APIRouter, HTTPException
from langfuse import observe, get_client
from src.models import TriageRequest, TriageResponse
from src.llm_client import extract_triage_from_log
from src.evaluator import score_triage
from src.database import write_triage_log

router = APIRouter(prefix="/api/v1", tags=["Triage"])


@router.post("/triage-alert", response_model=TriageResponse)
@observe(name="triage_pipeline")   # Opens the root Langfuse trace for this request
async def triage_alert(req: TriageRequest):
    """
    Full pipeline:
    1. LLM extracts structured data from raw log        (child span: llm_extraction)
    2. Evaluator scores the output vs PostgreSQL truth  (child span: evaluation_scorer)
    3. Score is pushed to the root trace in Langfuse
    4. Result is persisted to the audit log and returned
    """
    langfuse = get_client()

    # Step 1: LLM Extraction
    triage = extract_triage_from_log(req.raw_log)

    if triage is None:
        raise HTTPException(status_code=422, detail="LLM failed to produce valid JSON")

    # Step 2: Evaluation (DB query is auto-traced by OTel Psycopg2 → visible in HyperDX)
    trust_score, service_valid = score_triage(triage)

    # FIX F4: capture the real Langfuse trace ID while inside the @observe context
    trace_id = langfuse.get_current_trace_id()

    # FIX F5: push the trust score to the ROOT trace (not a child observation)
    # This makes it appear in the Langfuse Scores Chart at the pipeline level
    if trace_id:
        langfuse.score(
            trace_id=trace_id,
            name="trust_score",
            value=trust_score,
            comment=f"service_valid={service_valid}",
        )

    # Step 3: Persist to audit log (with real trace_id for cross-dashboard linking)
    write_triage_log(req.raw_log, triage, trust_score, trace_id=trace_id)

    return TriageResponse(
        triage=triage,
        trust_score=trust_score,
        service_valid=service_valid,
        langfuse_trace_id=trace_id,
    )
```

---

### Step 2.7 — `tests/sample_payloads.json`

Pre-built test cases that exercise all four trust-score buckets:

```json
[
  {
    "label": "perfect_match",
    "expected_trust_score": 1.0,
    "raw_log": "Connection timeout on auth-service at port 5432. Severity appears critical."
  },
  {
    "label": "hallucinated_service",
    "expected_trust_score": 0.5,
    "raw_log": "High CPU usage on fake-made-up-service. Disk I/O normal. Severity LOW."
  },
  {
    "label": "low_severity_real_service",
    "expected_trust_score": 1.0,
    "raw_log": "Latency spike on image-resizer. Slight slowdown, not urgent. Severity LOW."
  },
  {
    "label": "database_critical",
    "expected_trust_score": 1.0,
    "raw_log": "Fatal: user-billing-db is unreachable. All payment transactions failing."
  }
]
```

Run all four against the running server:

```bash
for payload in $(cat tests/sample_payloads.json | jq -c '.[]'); do
  echo "--- $(echo $payload | jq -r '.label') ---"
  curl -s -X POST http://localhost:8000/api/v1/triage-alert \
    -H "Content-Type: application/json" \
    -d "{\"raw_log\": $(echo $payload | jq '.raw_log')}" | jq .
done
```

---

### Step 2.8 — `tests/test_triage.py` — Unit + Integration Tests

> **What changed (M8):** The original plan listed this file but provided no content. Below is a complete, runnable test file.

```python
import pytest
from unittest.mock import patch, MagicMock
from src.models import AlertTriage
from src.evaluator import score_triage
from src.database import check_service_exists


# ---------------------------------------------------------------------------
# Unit tests — evaluator.py (no DB or LLM required)
# ---------------------------------------------------------------------------

class TestScoreTriage:
    def test_none_input_returns_zero(self):
        score, valid = score_triage(None)
        assert score == 0.0
        assert valid is False

    @patch("src.evaluator.check_service_exists", return_value=True)
    def test_perfect_triage_scores_one(self, mock_db):
        triage = AlertTriage(
            service_name="auth-service",
            severity_level="CRITICAL",
            is_database_issue=True,
        )
        score, valid = score_triage(triage)
        assert score == 1.0
        assert valid is True

    @patch("src.evaluator.check_service_exists", return_value=False)
    def test_hallucinated_service_scores_half(self, mock_db):
        triage = AlertTriage(
            service_name="made-up-service",
            severity_level="LOW",
            is_database_issue=False,
        )
        score, valid = score_triage(triage)
        assert score == 0.5   # 0.2 base + 0.3 valid severity, no +0.5
        assert valid is False

    @patch("src.evaluator.check_service_exists", return_value=True)
    def test_valid_service_all_severities(self, mock_db):
        for sev in ["LOW", "MEDIUM", "CRITICAL"]:
            triage = AlertTriage(
                service_name="checkout-api",
                severity_level=sev,
                is_database_issue=False,
            )
            score, valid = score_triage(triage)
            assert score == 1.0, f"Expected 1.0 for severity={sev}"


# ---------------------------------------------------------------------------
# Integration tests — POST /api/v1/triage-alert
# Requires: docker compose up -d  AND  uvicorn running
# Run with: pytest tests/test_triage.py -m integration
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestTriageEndpoint:
    BASE_URL = "http://localhost:8000/api/v1"

    def test_health_check(self):
        import httpx
        r = httpx.get("http://localhost:8000/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_valid_alert_returns_200_with_trust_score(self):
        import httpx
        payload = {"raw_log": "Connection timeout on auth-service port 5432, severity CRITICAL."}
        r = httpx.post(f"{self.BASE_URL}/triage-alert", json=payload)
        assert r.status_code == 200
        body = r.json()
        assert "trust_score" in body
        assert 0.0 <= body["trust_score"] <= 1.0
        assert "service_valid" in body
        assert body["triage"]["severity_level"] in {"LOW", "MEDIUM", "CRITICAL"}

    def test_empty_log_returns_422(self):
        import httpx
        r = httpx.post(f"{self.BASE_URL}/triage-alert", json={"raw_log": "ab"})
        assert r.status_code == 422  # Pydantic min_length=5 validation

    def test_langfuse_trace_id_is_returned(self):
        import httpx
        payload = {"raw_log": "Fatal: user-billing-db unreachable. All payments failing."}
        r = httpx.post(f"{self.BASE_URL}/triage-alert", json=payload)
        assert r.status_code == 200
        # FIX F4 verification: trace_id should no longer be null
        assert r.json().get("langfuse_trace_id") is not None
```

Run unit tests only (no infra needed):
```bash
pytest tests/test_triage.py -v -m "not integration"
```

Run all including integration (requires services running):
```bash
pytest tests/test_triage.py -v
```

---

## Full Program Flow Diagram

### Preparing Phase Flow

```
You (Developer)
     │
     ▼
[1] docker compose up -d
     ├── PostgreSQL:5432     ← schema.sql auto-seeds valid_services + triage_log
     │                          healthcheck ensures it's truly ready before Langfuse starts
     ├── HyperDX:8080        ← OTel collector (4317/4318) + UI (bundles ClickHouse internally)
     └── Langfuse:3000       ← AI trace UI (state stored in Postgres)
     │
     ▼
[2] python -m venv .venv && pip install -r requirements.txt
     │
     ▼
[3] cp .env.example .env && fill in OPENAI_API_KEY + Langfuse keys
    (Get Langfuse keys from http://localhost:3000 after first login)
     │
     ▼
[4] uvicorn src.main:app --reload
     │
     ▼
[5] curl http://localhost:8000/health
     └── Verify span appears in HyperDX UI → infra is 100% ready
```

### Real-Working Phase Flow (Per Request)

```
Client sends: POST /api/v1/triage-alert
  Body: { "raw_log": "Timeout on auth-service port 5432, retried 3x" }
         │
         ▼
[FastAPI + OTel]
  ┌─ HTTP span STARTS → HyperDX begins recording latency
  │
  ▼
[@observe("triage_pipeline")]        ← Langfuse ROOT trace OPENS
  │
  │  langfuse = get_client()         ← singleton, reads env vars automatically
  │
  ├──▶ [1] extract_triage_from_log(raw_log)
  │         │
  │         ├── @observe("llm_extraction")     ← Langfuse CHILD span
  │         ├── System prompt + user log → OpenAI gpt-4o-mini
  │         ├── Langfuse captures: prompt, raw response, token cost, latency
  │         └── Returns: AlertTriage(service_name="auth-service",
  │                                  severity_level="CRITICAL",
  │                                  is_database_issue=True)
  │
  ├──▶ [2] score_triage(triage)
  │         │
  │         ├── @observe("evaluation_scorer")  ← Langfuse CHILD span
  │         ├── Check: "CRITICAL" in VALID_SEVERITIES → +0.3
  │         ├── SQL: SELECT 1 FROM valid_services WHERE service_name='auth-service'
  │         │       └── OTel Psycopg2 auto-traces DB query → visible in HyperDX
  │         ├── DB returns row → service_valid=True → +0.5
  │         └── Returns: (1.0, True)
  │
  ├──▶ [3] langfuse.get_current_trace_id()   ← FIX F4: real ID, no longer None
  │         └── trace_id = "trace-abc-123"
  │
  ├──▶ [4] langfuse.score(trace_id="trace-abc-123", name="trust_score", value=1.0)
  │         └── FIX F5: score attached to ROOT trace → shows in Langfuse Scores Chart
  │
  ├──▶ [5] write_triage_log(raw, triage, 1.0, trace_id="trace-abc-123")
  │         └── INSERT → triage_log (langfuse_trace_id now populated for cross-linking)
  │
  └──▶ [6] Return TriageResponse
             {
               "triage": { "service_name": "auth-service",
                           "severity_level": "CRITICAL",
                           "is_database_issue": true },
               "trust_score": 1.0,
               "service_valid": true,
               "langfuse_trace_id": "trace-abc-123"
             }

HTTP span ENDS → HyperDX records total wall-clock time
Langfuse root trace CLOSES → dashboard shows full trace tree
On process shutdown → lifespan context flushes Langfuse batch queue (FIX M7)
```

---

## What You See in Each Dashboard

| Dashboard | What to Look For | What It Proves |
|---|---|---|
| **HyperDX Waterfall** | 3 spans: HTTP request → LLM call → Postgres query | You understand system-level observability |
| **HyperDX Timeline** | LLM latency (~500ms) dwarfs DB latency (~3ms) | You can identify real bottlenecks |
| **Langfuse Trace Tree** | `triage_pipeline` → `llm_extraction` → `evaluation_scorer` | You understand multi-step AI tracing |
| **Langfuse Scores Chart** | Run 4 sample payloads; scores show at root trace level | You can evaluate LLM quality automatically |
| **Langfuse Prompts** | Exact system prompt + token cost per call | You know how to track prompt engineering cost |
| **triage_log SQL query** | `SELECT service_name, trust_score, langfuse_trace_id FROM triage_log` | `langfuse_trace_id` is no longer NULL — cross-linking works |

---

## README Pitch Block (Copy-Paste Ready)

```markdown
## What This Is

An AI gateway that processes raw infrastructure alerts into structured JSON,
then immediately evaluates its own output for hallucinations using PostgreSQL
as a ground-truth source of truth.

## Observable At Two Levels

- **System level (HyperDX + OTel):** Every HTTP request, LLM call, and
  Postgres query is traced with nanosecond precision in a ClickHouse-backed
  waterfall UI.
- **AI level (Langfuse):** Every prompt, LLM response, token cost, and
  evaluation score (0.0–1.0) is recorded and dashboarded at the pipeline level.

## The Hallucination Detector

If the LLM invents a service name that doesn't exist in our database,
the trust_score drops to 0.5 — automatically flagging unreliable outputs
before they hit downstream systems.

## Stack

FastAPI · OpenTelemetry · HyperDX (ClickStack) · Langfuse v3 · PostgreSQL · SQLAlchemy 2 · gpt-4o-mini
```

---

## Quick-Reference: All Fixed Import Paths

```python
# llm_client.py and evaluator.py — Langfuse v3
from langfuse import observe, get_client      # NOT: from langfuse.decorators import ...

# triage.py — getting trace ID and scoring at root level
langfuse = get_client()
trace_id = langfuse.get_current_trace_id()
langfuse.score(trace_id=trace_id, name="trust_score", value=trust_score)

# main.py — flush on shutdown (lifespan pattern)
from contextlib import asynccontextmanager
@asynccontextmanager
async def lifespan(app):
    yield
    get_client().flush()
app = FastAPI(lifespan=lifespan)
```
