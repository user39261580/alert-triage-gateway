# Declare Route Handlers as def for Blocking I/O, Not async def

Status: accepted
Date: 2026-03-31
Deciders: ADR Bank Curation

## Context

- Calling synchronous blocking libraries (`requests`, `boto3`, `PIL`, synchronous SQLAlchemy) inside `async def` blocks the entire event loop for the duration of the call, stalling all in-flight requests.
- FastAPI emits no warning about this pattern, making it a silent performance degradation.
- FastAPI automatically offloads `def` route handlers to an external thread pool, preventing event loop blocking.
- The distinction between `def` and `async def` in FastAPI has significant runtime behavior differences that are not immediately obvious.

## Problem Statement

Using `async def` for route handlers that call synchronous blocking I/O libraries silently stalls the entire event loop, degrading throughput for all concurrent requests without any framework warning.

## Decision

1. MUST: Use `def` (not `async def`) for route handlers that call any synchronous blocking I/O library.
2. MUST: Use `async def` only when all I/O inside the handler uses `await`.
3. MUST: Never call `time.sleep()` inside `async def` — use `await asyncio.sleep()` instead.
4. SHOULD: Use `await asyncio.to_thread(cpu_bound_fn, *args)` for CPU-bound work inside `async def` handlers.

## Policy Block

- MUST use `def` (not `async def`) for route handlers that call any synchronous blocking I/O library.
- MUST use `async def` only when all I/O inside the handler uses `await`.
- MUST never call `time.sleep()` inside `async def`.
- SHOULD use `await asyncio.to_thread()` for CPU-bound work inside `async def` handlers.

In scope:
- FastAPI and Starlette route handler declarations
- Handlers calling `requests`, `boto3`, `PIL`, synchronous SQLAlchemy, or any non-async library
- `time.sleep()` vs `asyncio.sleep()` usage in async contexts
- Thread pool offloading for CPU-bound work

Out of scope:
- Background task workers and Celery task definitions
- WebSocket handlers (which have different concurrency requirements)
- Middleware implementations
- Non-FastAPI ASGI frameworks

Exceptions:
- EXC-001: `async def` with a single, brief synchronous call (e.g., reading a small in-memory cache) is acceptable when the blocking duration is negligible (< 1ms).

## Rationale

- FastAPI runs `def` handlers in a thread pool automatically, preventing any blocking call from stalling the event loop without requiring developer intervention.
- The `async def` / `def` distinction is a critical performance lever in ASGI frameworks, yet the failure mode (degraded throughput under load) only manifests in production-like conditions.
- Making this an explicit rule prevents a class of performance bugs that are invisible in single-request testing.

## Consequences

Positive:
- Prevents silent event loop stalls that degrade throughput for all concurrent requests.
- Leverages FastAPI's built-in thread pool offloading without additional boilerplate.
- Makes the concurrency model of each handler explicit and reviewable.

Negative:
- `def` handlers have slightly higher per-request overhead due to thread pool scheduling compared to native `async def` handlers.
- Developers must evaluate each handler's I/O stack to determine the correct declaration, adding cognitive load during code review.

## Alternatives

- Use `async def` everywhere and wrap blocking calls in `await asyncio.to_thread()` (rejected)
  Rejected because: It requires every blocking call site to be individually wrapped, which is error-prone and verbose compared to simply declaring the handler as `def`.
  When valid: When a handler mixes async and sync I/O calls and the async calls dominate, wrapping the few sync calls in `to_thread()` may be preferable.

## Risks

- Developers may default to `async def` out of habit or because IDE autocompletion suggests it, reintroducing blocking event loop calls.
  Mitigation: Add a linting rule or code review checklist item that flags `async def` handlers importing known synchronous libraries (`requests`, `boto3`, `PIL`).