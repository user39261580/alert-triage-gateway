# Use TestClient as a Context Manager to Trigger App Lifespan in Tests

Status: accepted
Date: 2026-03-31
Deciders: ADR Bank Curation

## Context

- Instantiating `TestClient(app)` at module scope does not trigger the lifespan context manager.
- Tests accessing `app.state` values set during startup see uninitialized state with no exception — the attribute is simply absent.
- The failure mode is silent: no error is raised, making the root cause difficult to diagnose.
- Async test suites using `httpx.AsyncClient` require additional setup to trigger lifespan events.

## Problem Statement

Using `TestClient(app)` without a context manager silently skips the application's lifespan events, causing tests that depend on startup-initialized state to fail with missing attributes rather than clear errors.

## Decision

1. MUST: Use `TestClient` as a context manager (`with TestClient(app) as client:`) in any test that depends on lifespan-initialized state.
2. MUST: For async test suites, use `httpx.AsyncClient` with `ASGITransport` and mark tests with `@pytest.mark.anyio`.
3. MUST: Mark async test functions with `@pytest.mark.anyio` — unmarked async test functions are silently skipped by pytest.
4. SHOULD: For `AsyncClient` lifespan triggers, install `asgi-lifespan` and wrap with `async with LifespanManager(app):`.

## Policy Block

- MUST use `TestClient` as a context manager (`with TestClient(app) as client:`) in any test that depends on lifespan-initialized state.
- MUST use `httpx.AsyncClient` with `ASGITransport` for async test suites.
- MUST mark async test functions with `@pytest.mark.anyio`.
- SHOULD use `asgi-lifespan` `LifespanManager` for `AsyncClient` lifespan triggers.

In scope:
- Starlette and FastAPI test suites using `TestClient` or `httpx.AsyncClient`
- Tests that depend on `app.state` values initialized during application startup
- Lifespan event triggering in both sync and async test contexts
- pytest configuration for async test discovery

Out of scope:
- Integration tests against running server instances (not using `TestClient`)
- Django or Flask test client patterns
- Application lifespan implementation itself (startup/shutdown handlers)

Exceptions:
- EXC-001: Tests that do not depend on any lifespan-initialized state may use `TestClient(app)` without a context manager for brevity.

## Rationale

- The context manager form ensures startup and shutdown lifespan events fire, matching production behavior and initializing all `app.state` values.
- Silent failures from missing `app.state` attributes waste significant debugging time because the root cause (skipped lifespan) is non-obvious.
- Requiring `@pytest.mark.anyio` on async tests prevents another class of silent test skipping.

## Consequences

Positive:
- Tests accurately reflect production application behavior by executing the full lifespan lifecycle.
- Eliminates a class of subtle, hard-to-diagnose test failures caused by uninitialized application state.
- Async test patterns are explicit and discoverable.

Negative:
- Slightly more verbose test setup compared to bare `TestClient(app)` instantiation.
- Async tests require additional dependencies (`asgi-lifespan`, `anyio`) and pytest markers.

## Alternatives

- Initialize test state manually in fixtures instead of relying on app lifespan (rejected)
  Rejected because: Duplicating startup logic in test fixtures drifts from production behavior and creates maintenance burden when lifespan handlers change.
  When valid: When testing components in isolation that should not depend on the full application lifecycle.

## Risks

- Developers unfamiliar with the pattern may still use bare `TestClient(app)` without the context manager, reintroducing silent failures.
  Mitigation: Add a project-level pytest fixture that always yields a context-managed `TestClient`, and lint for bare `TestClient(app)` instantiations in test files.