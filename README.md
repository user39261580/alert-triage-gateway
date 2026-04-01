# 🚨 Alert Triage Gateway

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/postgresql-%23316192?style=for-the-badge&logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/docker-%230db7ed?style=for-the-badge&logo=docker&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white)
![OpenTelemetry](https://img.shields.io/badge/OpenTelemetry-000000?style=for-the-badge&logo=opentelemetry&logoColor=white)
![ClickHouse](https://img.shields.io/badge/ClickHouse-FFCC01?style=for-the-badge&logo=clickhouse&logoColor=white)
![Langfuse](https://img.shields.io/badge/Langfuse-000000?style=for-the-badge&logoColor=white)
![Perplexity](https://img.shields.io/badge/perplexity-000000?style=for-the-badge&logo=perplexity&logoColor=088F8F)
![GitHub Copilot](https://img.shields.io/badge/github_copilot-8957E5?style=for-the-badge&logo=github-copilot&logoColor=white)

> **When an LLM-powered API breaks in production, there are two completely different reasons it could fail — and they need two completely different observability tools to diagnose.**
>
> This project instruments both at once.

---

## The Problem It Solves

Most LLM-in-production monitoring stacks answer one of two questions:

- *"Is the infrastructure slow?"* → APM / distributed tracing
- *"Is the model hallucinating?"* → LLM evaluation / scoring

In practice you need **both answered simultaneously**, with a shared trace ID so you can correlate a bad user experience to its exact root cause — infra or model — in seconds.

This API demonstrates that dual-layer architecture in a single, self-contained pipeline.

---

## What It Does

Send any raw, messy infrastructure log string to `POST /api/v1/triage-alert`.

The pipeline:

1. **Extracts** structured signal from the raw text using an LLM (`gpt-4o-mini` by default) — outputting `service_name`, `severity_level`, and `is_database_issue` as strict JSON
2. **Evaluates** the LLM's own output immediately: checks the extracted service name against a PostgreSQL ground-truth table of known services
3. **Scores** the response with a `trust_score` between `0.0` and `1.0` based on output validity and hallucination detection
4. **Emits dual telemetry** — system spans to HyperDX via OpenTelemetry, AI traces and scores to Langfuse — linked by the same trace ID
5. **Writes an audit log** to PostgreSQL with every result, including the Langfuse trace ID for cross-dashboard navigation

### Trust Score Breakdown

```
+0.2  — LLM returned parseable JSON (not None / not a crash)
+0.3  — severity_level is a valid enum: LOW | MEDIUM | CRITICAL
+0.5  — service_name exists in PostgreSQL valid_services table
────
 1.0  — full trust: structured output + known service
 0.5  — valid structure, hallucinated service name
 0.2  — returned something, but invalid severity + unknown service
 0.0  — LLM returned unparseable output entirely
```

---

## Live Example

```bash
curl -s -X POST http://localhost:8000/api/v1/triage-alert \
  -H "Content-Type: application/json" \
  -d '{"raw_log": "Connection timeout on auth-service at port 5432. Severity appears CRITICAL."}'
```

```json
{
  "triage": {
    "service_name": "auth-service",
    "severity_level": "CRITICAL",
    "is_database_issue": true
  },
  "trust_score": 1.0,
  "service_valid": true,
  "langfuse_trace_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

Now try a log with a plausible-but-fake service name:

```bash
curl -s -X POST http://localhost:8000/api/v1/triage-alert \
  -H "Content-Type: application/json" \
  -d '{"raw_log": "High CPU on payments-processor-v2. Disk IO normal. Severity LOW."}'
```

```json
{
  "triage": {
    "service_name": "payments-processor-v2",
    "severity_level": "LOW",
    "is_database_issue": false
  },
  "trust_score": 0.5,
  "service_valid": false,
  "langfuse_trace_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7"
}
```

`trust_score: 0.5` — the model gave valid JSON and a real severity, but hallucinated a service name that doesn't exist in the ground-truth table. That's the signal.

---

## The Dual Observability Split

This is the architectural core of the project. One request generates two independent telemetry streams — both stamped with the same trace ID.

| Failure mode                                                 | Where to look                                           | What you see                                                                    |
| ------------------------------------------------------------ | ------------------------------------------------------- | ------------------------------------------------------------------------------- |
| **Infra is slow** (DB overloaded, network latency)           | **HyperDX** (OTel)                                      | Span waterfall — `http_handler` → `llm_call` → `db_query`, with P99 per span    |
| **LLM is hallucinating** (wrong service names, bad severity) | **Langfuse**                                            | `trust_score` chart trending down, trace tree showing the exact prompt + output |
| **Both happening**                                           | Cross-reference via `langfuse_trace_id` in `triage_log` | Same request, two dashboards, instant root cause                                |

> **The key insight:** HyperDX tells you *when* something is slow. Langfuse tells you *whether* the model can still be trusted. Without both, you're flying half-blind.

### HyperDX — System Trace Waterfall

*Every request produces a 3-span waterfall: HTTP handler wraps the LLM call, which is sibling to the DB lookup. Slow DB ≠ bad model. You can now tell them apart.*

<!-- 📸 INSERT SCREENSHOT: HyperDX span waterfall showing the 3-span hierarchy:
     http_handler (total) → llm_extraction (child) + db_lookup (child)
     Ideal: show one request where LLM latency is visibly the bottleneck -->

### Langfuse — AI Trace Tree + Trust Scores

*Every LLM call is traced with its full prompt, raw output, token count, and the computed trust score pushed as a named Score. Filter by `requested_model` metadata to compare models side by side.*

<!-- 📸 INSERT SCREENSHOT: Langfuse trace tree showing:
     triage_pipeline (root) → llm_extraction (generation) → evaluation_scorer
     With the trust_score visible as a Score on the root trace -->

<!-- 📸 INSERT SCREENSHOT: Langfuse Scores Chart
     Show trust_score distribution across multiple runs / payload types
     Ideal: visible spread between 0.0, 0.5, 1.0 scores across different payloads -->

---

## Architecture

```
POST /api/v1/triage-alert
        │
        ▼
[ FastAPI + OTel ]  ──────────────────────▶  HyperDX   (system traces, span waterfall)
        │
        ▼
[ LLM Extraction ]  ──────────────────────▶  Langfuse  (AI traces, token cost, prompt)
   gpt-4o-mini · Pydantic JSON schema
        │
        ▼
[ Evaluator ]
   ├── Parseable JSON?      +0.2
   ├── Valid severity enum? +0.3
   └── Service in DB?       +0.5  ◀──  PostgreSQL ground-truth (valid_services)
        │
        ▼
[ Trust Score ]  ─────────────────────────▶  Langfuse  (Score on root trace)
        │
        ▼
[ Audit Log ]  ───────────────────────────▶  PostgreSQL triage_log
                                              (with langfuse_trace_id for cross-linking)
```

---

## Tech Stack

| Layer            | Technology           | Role                                                         |
| ---------------- | -------------------- | ------------------------------------------------------------ |
| API              | FastAPI + Uvicorn    | Async HTTP, Pydantic-native request/response validation      |
| LLM              | OpenAI `gpt-4o-mini` | Structured JSON extraction from unstructured log text        |
| AI Tracing       | Langfuse v3          | Prompt traces, token cost, eval scores per run               |
| System Tracing   | OpenTelemetry + OTLP | Standard distributed tracing across all spans                |
| Observability UI | HyperDX              | ClickHouse-backed OTel collector + UI, single Docker service |
| Database         | PostgreSQL 15        | Ground-truth service registry + immutable audit log          |
| ORM              | SQLAlchemy 2.0       | Sync connection pool with context-manager session handling   |
| Infra            | Docker Compose       | Full stack in one command — no manual service wiring         |
| Testing          | pytest + httpx       | Unit tests (mocked LLM + DB) and integration tests           |

---

## Quick Start

**Prerequisites:** Docker, an OpenAI API key, a Langfuse project (public + secret key).

```bash
git clone https://github.com/user39261580/alert-triage-gateway.git
cd alert-triage-gateway

cp .env.example .env
# Fill in: OPENAI_API_KEY, LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY

docker compose up -d
```

The stack starts PostgreSQL, HyperDX, and the FastAPI app. Schema and seed data auto-apply on first boot.

```bash
# Verify it's up
curl http://localhost:8000/health

# Run your first triage
curl -s -X POST http://localhost:8000/api/v1/triage-alert \
  -H "Content-Type: application/json" \
  -d '{"raw_log": "Fatal: user-billing-db is unreachable. All payment transactions failing."}'
```

Then open:
- **HyperDX UI:** `http://localhost:8080`
- **Langfuse UI:** `https://us.cloud.langfuse.com/`

---

## Test Suite

```bash
# Unit tests — no infrastructure required, LLM and DB are mocked
uv run pytest tests/test_triage.py -v

# Integration tests — requires docker compose up -d
uv run pytest tests/test_triage.py -v -m integration
```

---

## Multi-Model Comparison

The API accepts an optional `model` field on every request, defaulting to `gpt-4o-mini`. The included `compare_models.py` script runs the full payload suite across multiple models in one pass:

```bash
python tests/compare_models.py
```

Default model lineup: `gpt-4o-mini`, `gpt-5.4-mini`, `gpt-5.4-nano`

Output per run:

```
model,label,status_code,trust_score,expected_trust_score,service_valid,latency_ms,trace_id
gpt-4o-mini,perfect_match,200,1.0,1.0,True,2089.3,ad9a97ed...
gpt-4o-mini,hallucinated_service,200,0.5,0.5,False,2052.24,9053f4f7...
gpt-4o-mini,unparseable_noise,200,0.5,0.0,False,982.63,391229a4...
gpt-5.4-mini,perfect_match,200,1.0,1.0,True,528.77,32b9b3a4...
gpt-5.4-mini,hallucinated_service,200,0.5,0.5,False,605.52,32247f9f...
gpt-5.4-mini,unparseable_noise,200,0.5,0.0,False,1221.09,d10d9831...
gpt-5.4-nano,perfect_match,200,1.0,1.0,True,859.12,9a37ade9...
gpt-5.4-nano,hallucinated_service,200,0.5,0.5,False,601.18,ae87abf1...
gpt-5.4-nano,unparseable_noise,200,0.5,0.0,False,515.66,b6a1ece7...

Summary
- gpt-4o-mini: runs=10  avg_trust_score=0.8  avg_latency_ms=1730.35
- gpt-5.4-mini: runs=10  avg_trust_score=0.8  avg_latency_ms=963.01
- gpt-5.4-nano: runs=10  avg_trust_score=0.8  avg_latency_ms=776.22
```

Use the `trace_id` column to open any individual run directly in Langfuse and inspect the exact prompt, completion, and score.

<!-- 📸 INSERT SCREENSHOT (optional / if you run it): compare_models.py terminal output
     OR a Langfuse dashboard filtered by model showing avg trust_score per model
     This section is compelling even as text-only if no screenshot is available -->

### Payload Coverage

The test suite covers the full trust score spectrum plus real-world edge cases:

| Label                                | Raw Log Summary                                       | Expected Score | Tests                                                      |
| ------------------------------------ | ----------------------------------------------------- | -------------- | ---------------------------------------------------------- |
| `perfect_match`                      | `auth-service` CRITICAL timeout                       | `1.0`          | Valid JSON + valid severity + known service                |
| `database_critical`                  | `user-billing-db` unreachable                         | `1.0`          | DB issue flagged correctly                                 |
| `hallucinated_service`               | Plausible but fake service name                       | `0.5`          | Model invents a service not in registry                    |
| `typo_near_miss_service`             | `autth-service` (typo)                                | `0.5`          | Near-match name should not pass service validation         |
| `ambiguous_severity_503`             | Intermittent 503s, unclear degraded vs down state     | `0.5`          | Tests model confidence on ambiguous severity clues         |
| `multi_service_cascade`              | Cascade across 3 known services                       | `1.0`          | Model picks correct root cause service                     |
| `structured_log_datadog_style`       | Pre-formatted `[CRITICAL][user-billing-db]` log       | `1.0`          | Model handles structured/SIEM style format cleanly         |
| `misleading_noise_with_real_service` | `auth-service` responded in 2ms, no issues            | `1.0`          | Real service mention amid noisy text still scores high     |
| `mixed_language_partial_spanish`     | Spanish/English mixed outage signal on `auth-service` | `1.0`          | Tests multilingual robustness with real service extraction |
| `unparseable_noise`                  | `%%%% #### ???? !!!` token noise                      | `0.0`          | Model returns unparseable output                           |

---

## Project Origin

Built in one day for the **[Seattle Startup Summit 2026](https://www.seattlestartupsummit.com/early-stage-startups)**.

Before writing a single line of code, I used **Perplexity AI** to research and cluster 50+ attending companies by domain and tech stack. The goal was to identify a *Greatest Common Factor* architecture — one project that would simultaneously speak to the core problems of AI infrastructure, observability, and agent reliability companies.

The answer was a self-evaluating LLM pipeline, because every company in that cluster is dealing with the same unsolved question: *you cannot blindly trust LLM outputs in production, and you need both system-level and AI-level visibility to know exactly why things fail.*

> 🤖 This project was developed in full collaboration with AI — from landscape research and architecture planning, to implementation and debugging. The entire workflow was a deliberate human + AI co-development loop.
>
> 👉 **[View the full Perplexity AI research space here](https://www.perplexity.ai/spaces/pitch-project-for-startup-summ-guvS7IblQTa0ecXqzgDVyw)**

### Why This Stack Resonates

| Company                       | Domain                             | Connection                                              |
| ----------------------------- | ---------------------------------- | ------------------------------------------------------- |
| **Okahu**                     | AI observability for LLM apps      | Demonstrates exactly the observability layer they sell  |
| **Datawizz**                  | SLM training + continuous learning | Mirrors their eval loop + runtime signal philosophy     |
| **Oumi**                      | Automated model evaluation         | Shows automated 0.0–1.0 scoring per LLM run             |
| **Exosphere**                 | Agent reliability manager          | Structured output enforcement + run tracking            |
| **StratoCloud / Cielara**     | Cloud intelligence                 | Service hallucination = config drift, same root problem |
| **Actual AI / CodeIntegrity** | Agent governance                   | Audit log + guardrail-style evaluation                  |

### AI-Assisted Development Workflow

| Stage              | What Happened                                                                                                                     |
| ------------------ | --------------------------------------------------------------------------------------------------------------------------------- |
| **Research**       | Perplexity analyzed 50+ Summit companies, clustered by stack, ranked hiring potential                                             |
| **Architecture**   | 3 business logic options generated and compared; Alert Triage Gateway selected as highest-resonance                               |
| **Implementation** | All source files written iteratively with AI, bugs caught and fixed through dialogue                                              |
| **Debugging**      | 10 bugs resolved collaboratively: Langfuse v3 imports, OTel endpoint format, SQLAlchemy 2.0 session handling, Docker healthchecks |

---

## File Structure

```
alert-triage-gateway/
├── docker-compose.yml        # PostgreSQL + HyperDX + app
├── schema.sql                # Auto-seeds valid_services + creates triage_log
├── .env.example              # All required secrets documented
├── requirements.txt
├── src/
│   ├── main.py               # FastAPI app + OTel bootstrap + lifespan flush
│   ├── models.py             # Pydantic schemas: TriageRequest, AlertTriage, TriageResponse
│   ├── database.py           # PostgreSQL pool (SQLAlchemy 2.0 sync)
│   ├── llm_client.py         # LLM call + Langfuse @observe tracing
│   ├── evaluator.py          # Trust score: +0.2 / +0.3 / +0.5 logic
│   ├── telemetry.py          # OTel tracer setup + span helpers
│   └── routers/
│       └── triage.py         # POST /api/v1/triage-alert full pipeline
└── tests/
    ├── test_triage.py        # Unit + integration tests
    ├── sample_payloads.json  # Edge-case payload suite
    └── compare_models.py     # Multi-model benchmark runner
```
