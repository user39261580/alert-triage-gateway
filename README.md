# 🚨 Dual-Observable Alert Triage Gateway

![Perplexity](https://img.shields.io/badge/perplexity-000000?style=for-the-badge&logo=perplexity&logoColor=088F8F)
![GitHub Copilot](https://img.shields.io/badge/github_copilot-8957E5?style=for-the-badge&logo=github-copilot&logoColor=white)
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/postgresql-%23316192?style=for-the-badge&logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/docker-%230db7ed?style=for-the-badge&logo=docker&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white)
![OpenTelemetry](https://img.shields.io/badge/OpenTelemetry-000000?style=for-the-badge&logo=opentelemetry&logoColor=white)
![ClickHouse](https://img.shields.io/badge/ClickHouse-FFCC01?style=for-the-badge&logo=clickhouse&logoColor=white)

> ⚠️ **Status: In Progress** — This project is actively being built. This README documents the plan, motivation, and current progress.

---

## 💡 Origin & Motivation

I'm attending the **[Seattle Startup Summit 2026](https://www.seattlestartupsummit.com/early-stage-startups)** and wanted to build something real to show — not a tutorial clone, but a project that speaks directly to the problems early-stage AI infrastructure companies are actually solving.

Before writing a single line of code, I used **Perplexity AI** to research and analyze 50+ companies attending the summit. I clustered them by domain, studied their product language, and identified a **Greatest Common Factor stack** — a single project architecture that would resonate with the broadest set of well-funded AI infra startups simultaneously.

The question I was trying to answer: *"What is the one project I can build in a day that would make a Datawizz, Okahu, or Oumi engineer immediately want to keep talking to me?"*

The answer: **a self-evaluating LLM pipeline** — because every one of these companies is dealing with the same core problem: you cannot blindly trust LLM outputs in production, and you need both system-level and AI-level visibility to know exactly why things fail.

> 🤖 **This project was developed in collaboration with AI** — from company landscape research, brainstorming, stack selection, and architecture planning, to implementation and iterative debugging. The entire workflow was a real human + AI co-development loop.
>
> 👉 **[View the full Perplexity AI collaboration space here](https://www.perplexity.ai/spaces/pitch-project-for-startup-summ-guvS7IblQTa0ecXqzgDVyw)**

---

## 🎯 What I'm Building

A lightweight **Alert Triage API** that:

1. Receives a raw, messy infrastructure error string (e.g. `"Timeout on port 5432 connecting to user-billing-db, retried 3x"`)
2. Uses an LLM (`gpt-4o-mini`) to extract it into a strict JSON schema — `service_name`, `severity_level`, `is_database_issue`
3. **Immediately evaluates the LLM's own output** by checking if the extracted service name actually exists in a PostgreSQL ground-truth table
4. Assigns a **Trust Score (0.0 – 1.0)** and pushes it to Langfuse, so I can track hallucination rates over time
5. Exposes the entire pipeline — HTTP latency, LLM call time, DB query time — as OpenTelemetry traces visible in HyperDX

The pitch: *"If this API starts failing, I can instantly tell whether it's the database lagging (HyperDX) or the LLM hallucinating fake service names (Langfuse) — because I'm observing both layers at once."*

---

## 🏗️ Planned Architecture

```
POST /api/v1/triage-alert
        │
        ▼
[ FastAPI + OTel ]  ──────────────────────▶  HyperDX   (system traces)
        │
        ▼
[ LLM Extraction ]  ──────────────────────▶  Langfuse  (AI traces + token cost)
   gpt-4o-mini · Pydantic JSON schema
        │
        ▼
[ Evaluator ]
   ├── Valid JSON?           +0.2
   ├── Valid severity enum?  +0.3
   └── Service in DB?        +0.5  ◀──  PostgreSQL ground-truth
        │
        ▼
[ Trust Score ]  ─────────────────────────▶  Langfuse  (root trace score)
        │
        ▼
[ Audit Log ]  ───────────────────────────▶  PostgreSQL `triage_log`
```

---

## 🧱 Tech Stack

| Layer            | Technology           | Reason                                         |
| ---------------- | -------------------- | ---------------------------------------------- |
| API              | FastAPI + Uvicorn    | Fast, async, Pydantic-native                   |
| LLM              | OpenAI `gpt-4o-mini` | Cheap, reliable JSON mode                      |
| AI Tracing       | Langfuse v3          | Traces prompts, tokens, eval scores            |
| System Tracing   | OpenTelemetry + OTLP | Standard infra observability                   |
| Observability UI | HyperDX (all-in-one) | Bundles ClickHouse + OTel collector            |
| Database         | PostgreSQL 15        | Ground truth + audit log                       |
| ORM              | SQLAlchemy 2.0       | Async-compatible, context manager style        |
| Infra            | Docker Compose       | Single `docker compose up -d` for all services |
| Testing          | pytest + httpx       | Unit + integration coverage                    |

---

## 📁 Planned File Structure

```
alert-triage-gateway/
├── docker-compose.yml       # PostgreSQL + HyperDX + Langfuse
├── schema.sql               # Auto-seeds valid_services + triage_log
├── requirements.txt
├── .env.example
├── src/
│   ├── main.py              # FastAPI app + OTel bootstrap + lifespan
│   ├── models.py            # Pydantic schemas
│   ├── database.py          # PostgreSQL pool (SQLAlchemy 2.0)
│   ├── llm_client.py        # LLM call + Langfuse tracing
│   ├── evaluator.py         # Trust score logic
│   └── routers/
│       └── triage.py        # POST /api/v1/triage-alert
└── tests/
    ├── test_triage.py
    └── sample_payloads.json  # 4 test cases covering all trust-score buckets
```

---

## ✅ Build Progress

### Phase 1 — Infrastructure
- [ ] `docker-compose.yml` — PostgreSQL + HyperDX + Langfuse
- [ ] `schema.sql` — seed `valid_services` and `triage_log` tables
- [ ] `.env.example` — document all required secrets
- [ ] Python virtual environment + `requirements.txt`

### Phase 2 — Core Application
- [ ] `src/models.py` — Pydantic schemas (`TriageRequest`, `TriageResponse`, `AlertTriage`)
- [ ] `src/database.py` — PostgreSQL connection pool and helper functions
- [ ] `src/llm_client.py` — LLM call with Langfuse `@observe` tracing
- [ ] `src/evaluator.py` — Trust score computation (JSON validity + enum check + DB lookup)
- [ ] `src/routers/triage.py` — `POST /api/v1/triage-alert` full pipeline endpoint
- [ ] `src/main.py` — FastAPI app, OTel bootstrap, lifespan flush

### Phase 3 — Testing & Validation
- [ ] `tests/sample_payloads.json` — 4 test cases (perfect match, hallucinated service, low severity, DB critical)
- [ ] `tests/test_triage.py` — unit tests (no infra) + integration tests
- [ ] Confirm `trust_score` appears in Langfuse Scores Chart at root trace level
- [ ] Confirm `langfuse_trace_id` is non-null in `triage_log` (cross-dashboard linking)
- [ ] Confirm 3-span waterfall in HyperDX (HTTP → LLM → Postgres)

---

## 🔬 Multi-Model Comparison Run

The triage request accepts an optional `model` field and defaults to `gpt-4o-mini`, so existing tests and CI behavior are unchanged.

Run the same payload dataset across three models:

```bash
python tests/compare_models.py
```

Default lineup:
- `gpt-4o-mini`
- `gpt-5.4-nano`
- `gpt-5.4-mini`

The script prints one row per `(model, payload)` with:
- HTTP status
- trust score
- latency
- `langfuse_trace_id`

Use those trace IDs (or filter by `requested_model` metadata in Langfuse) to compare cost, latency, and score side-by-side in dashboards.

### Phase 4 — Demo Prep
- [ ] Screenshot: HyperDX waterfall showing LLM latency vs. DB latency
- [ ] Screenshot: Langfuse trace tree (`triage_pipeline` → `llm_extraction` → `evaluation_scorer`)
- [ ] Screenshot: Langfuse Scores Chart across 4 sample payloads
- [ ] Update README with actual results and dashboard screenshots

---

## 🏢 Target Companies at Seattle Startup Summit 2026

The project is specifically designed to resonate with companies in the **AI infra, observability, and agent reliability** cluster attending the summit:

| Company                              | Domain                              | Why This Project Connects                              |
| ------------------------------------ | ----------------------------------- | ------------------------------------------------------ |
| **Datawizz**                         | SLM training + continuous learning  | Mirrors their eval loop + runtime signals philosophy   |
| **Okahu**                            | AI observability for LLM apps       | Demonstrates exactly the observability layer they sell |
| **Oumi**                             | Automated model evaluation          | Shows automated scoring (0.0–1.0) per LLM run          |
| **Exosphere**                        | Agent reliability manager           | Shows structured output enforcement + run tracking     |
| **StratoCloud / Cielara / JigsawML** | Cloud intelligence + digital twin   | Service hallucination = config drift, same problem     |
| **Actual AI / CodeIntegrity**        | Engineering mgmt + agent governance | Audit log, run history, guardrail-style evaluation     |

---

## 🤝 AI-Assisted Development Workflow

This project is an example of a **full AI co-pilot workflow from 0 to deployed**:

| Stage              | What Was Done                                                                                                                                |
| ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------- |
| **Research**       | Perplexity analyzed 50+ Summit companies, extracted tech stack patterns, and ranked hiring potential                                         |
| **Brainstorm**     | 3 business logic options were generated and compared; Alert Triage Gateway was selected as highest-resonance                                 |
| **Architecture**   | Full system design, file structure, and Docker Compose setup planned with AI assistance                                                      |
| **Implementation** | Code for all 7 source files written iteratively, with bugs caught and fixed through AI dialogue                                              |
| **Debugging**      | 10 identified bugs (Langfuse v3 imports, OTel endpoint format, SQLAlchemy 2.0 context manager, Docker healthchecks) resolved collaboratively |

> 👉 **[See the full research + planning conversation in this Perplexity Space](https://www.perplexity.ai/spaces/pitch-project-for-startup-summ-guvS7IblQTa0ecXqzgDVyw)**