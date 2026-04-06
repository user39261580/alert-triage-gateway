# Restrict FastAPI BackgroundTasks to Fast, Non-Retriable Work

Status: accepted
Date: 2026-03-31
Deciders: ADR Bank Curation

## Context

- FastAPI's `BackgroundTasks` runs tasks in the same process after the HTTP response is sent.
- There is no queue, no retry mechanism, and no persistence backing `BackgroundTasks`.
- Tasks that raise an exception or run too long are silently dropped with no error surfaced to the caller.
- Any server restart or unhandled process-level exception causes all in-flight background tasks to be lost.
- Using `BackgroundTasks` for email delivery, file processing, or external API calls creates invisible data loss.

## Problem Statement

`BackgroundTasks` provides no durability guarantees — failed or interrupted tasks are silently lost with no retry or dead-letter queue. Using it for work that must complete reliably (email, payments, webhooks, file processing) creates invisible data loss that is difficult to detect and diagnose in production.

## Decision

1. MUST: Use `BackgroundTasks` only for fast (sub-100ms), fire-and-forget work where task loss is acceptable.
2. MUST: Use a persistent task queue (Celery, ARQ, or Dramatiq) for any work that must complete reliably or be retried on failure.

## Policy Block

- MUST use `BackgroundTasks` only for fast (sub-100ms), fire-and-forget work where task loss is acceptable.
- MUST use a persistent task queue (Celery, ARQ, or Dramatiq) for any work that must complete reliably or be retried on failure.

In scope:
- FastAPI `BackgroundTasks` usage classification and scoping within route handlers.
- Selection criteria for choosing between `BackgroundTasks` and a persistent task queue.
- Guidance on durable async task queue options (Celery, ARQ, Dramatiq) compatible with FastAPI.

Out of scope:
- Temporal workflow scheduling for long-running or complex orchestration (covered by separate ADRs).
- Internal configuration and deployment of Celery, ARQ, or Dramatiq brokers.
- Cron-style scheduled task patterns.

Exceptions:
- EXC-001: None currently documented.

## Rationale

- `BackgroundTasks` is designed for lightweight post-response work such as writing audit logs or invalidating cache entries where occasional loss is tolerable — it is explicitly not a substitute for a proper task queue.
- Using a persistent queue for critical work (email, payment webhooks) provides retry semantics, observability via task status, and durability across process restarts that `BackgroundTasks` fundamentally cannot offer.

## Consequences

Positive:
- Critical background work is durably queued and retried on failure, eliminating silent data loss for important operations.
- `BackgroundTasks` remains the correct tool for its intended sub-100ms fire-and-forget use case, keeping those integrations simple.

Negative:
- Introducing a persistent task queue adds infrastructure complexity: a message broker, worker processes, monitoring, and dead-letter queue handling.
- Developers must consciously classify background work as fire-and-forget vs. must-complete before choosing the mechanism, which adds a decision step.

## Alternatives

- Use `asyncio.create_task()` for all background work (rejected)
  Rejected because: Like `BackgroundTasks`, `asyncio.create_task()` has no persistence or retry semantics and tasks are lost on process restart or unhandled exceptions — it does not solve the durability problem.
  When valid: For in-process coordination of short-lived async coroutines with explicit cancellation and error handling, not for durable work.

## Risks

- Developers may not realize `BackgroundTasks` has no retry, treating it as a lightweight task queue for moderately important work.
  Mitigation: Document the sub-100ms / fire-and-forget constraint with an inline comment at every `add_task()` call site and enforce via code review for any task that involves network I/O or external service calls.