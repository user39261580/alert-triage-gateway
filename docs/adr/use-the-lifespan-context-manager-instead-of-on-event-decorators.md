# Use the Lifespan Context Manager Instead of on_event Decorators

Status: accepted
Date: 2026-03-31
Deciders: ADR Bank Curation

## Context

- FastAPI 0.93 deprecated @app.on_event in favor of the lifespan= parameter.
- When both lifespan and @app.on_event are present, all @app.on_event handlers silently stop executing with no warning or error at startup.
- This silent suppression means critical startup/shutdown logic (database connections, cache warming, background tasks) can be lost without any indication.
- The lifespan context manager provides a single, structured location for all application lifecycle logic.

## Problem Statement

Mixing @app.on_event decorators with a lifespan context manager in FastAPI 0.93+ causes all on_event handlers to silently stop executing, potentially dropping critical startup and shutdown logic (database pools, cache connections, background workers) with no error or warning.

## Decision

1. MUST: Define all startup and shutdown logic in an @asynccontextmanager function passed as lifespan= to FastAPI().
2. MUST: Never use @app.on_event('startup') or @app.on_event('shutdown') in FastAPI 0.93+.
3. MUST: Pass the lifespan at construction time: app = FastAPI(lifespan=lifespan).
4. SHOULD: In tests, use `with TestClient(app) as client:` to trigger lifespan — bare instantiation does not.

## Policy Block

- MUST define all startup and shutdown logic in an @asynccontextmanager function passed as lifespan= to FastAPI().
- MUST never use @app.on_event('startup') or @app.on_event('shutdown') in FastAPI 0.93+.
- MUST pass the lifespan function at FastAPI construction time.
- SHOULD use the context manager form of TestClient in tests to trigger lifespan events.

In scope:
- FastAPI application lifecycle management (startup/shutdown)
- FastAPI 0.93+ lifespan parameter configuration
- Test client setup that requires lifespan execution

Out of scope:
- Starlette-only applications not using FastAPI
- Background task scheduling (Celery, APScheduler) beyond initial startup registration
- Middleware lifecycle that is independent of application lifespan

Exceptions:
- EXC-001: Legacy codebases on FastAPI < 0.93 where lifespan is not available may continue using @app.on_event until the framework is upgraded.

## Rationale

- The lifespan context manager provides a single, auditable location for all startup and shutdown logic, reducing the chance of missed cleanup.
- The silent suppression of on_event handlers when lifespan is present makes mixing the two approaches a high-severity latent bug.
- The @asynccontextmanager pattern naturally pairs startup with its corresponding shutdown via yield, preventing resource leak from forgotten cleanup.

## Consequences

Positive:
- All lifecycle logic is consolidated in one function, making it easy to audit and maintain.
- Startup and shutdown are naturally paired via yield, preventing orphaned resources.
- No risk of silent handler suppression from mixing old and new APIs.

Negative:
- Migrating existing @app.on_event handlers requires restructuring them into a single async context manager, which can be non-trivial for applications with many independent startup steps.
- Developers familiar with the on_event pattern need to learn the new approach.

## Alternatives

- Continue using @app.on_event decorators exclusively without lifespan (rejected)
  Rejected because: The API is deprecated as of FastAPI 0.93 and will eventually be removed. Additionally, on_event does not naturally pair startup with shutdown, increasing the risk of resource leaks.
  When valid: Only in codebases pinned to FastAPI < 0.93 where upgrading is not feasible.

## Risks

- A developer adds an @app.on_event handler without realizing lifespan is configured, silently disabling their new handler.
  Mitigation: Add a linting rule or startup assertion that searches for @app.on_event usage and raises an error if lifespan is also configured.