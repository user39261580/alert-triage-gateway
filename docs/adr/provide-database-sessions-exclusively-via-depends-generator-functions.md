# Provide Database Sessions Exclusively via Depends() Generator Functions

Status: accepted
Date: 2026-03-31
Deciders: ADR Bank Curation

## Context

- Creating database sessions as module-level globals bypasses FastAPI's request lifecycle entirely.
- Sessions instantiated directly inside route handler bodies are not guaranteed to close when an exception occurs.
- Sessions created outside `Depends()` cannot be replaced by test overrides without monkey-patching global state.
- Unmanaged sessions that are not reliably closed cause connection pool exhaustion under load.

## Problem Statement

Database sessions created outside FastAPI's dependency injection system are not scoped to the request lifecycle, causing connection leaks on errors and preventing clean test isolation. Using `Depends()` generator functions ensures sessions are always opened and closed correctly regardless of success or failure.

## Decision

1. MUST: Provide all database sessions via a `Depends()` generator function — never instantiate `Session` or `AsyncSession` directly inside a route handler body or as a module-level global.

## Policy Block

- MUST provide all database sessions via a `Depends()` generator function — never instantiate `Session` or `AsyncSession` directly inside a route handler body or as a module-level global.

In scope:
- SQLAlchemy `Session` and `AsyncSession` lifecycle management in FastAPI applications.
- Dependency injection patterns for database access in route handlers and service layers.
- Test overrides for database sessions via `app.dependency_overrides`.

Out of scope:
- Database connections managed outside the request scope, such as background workers, CLI scripts, or startup/shutdown event handlers.
- Non-SQLAlchemy database clients such as raw `asyncpg` connections or Redis clients.
- Script or migration contexts where FastAPI DI is not used.

Exceptions:
- EXC-001: None currently documented.

## Rationale

- FastAPI's `Depends()` with a generator ensures the `finally` block (session close) executes even when the route handler raises an exception, reliably returning connections to the pool.
- Dependency injection makes the session replaceable in tests without modifying production code, enabling proper isolation via `app.dependency_overrides`.

## Consequences

Positive:
- Connections are reliably returned to the pool after every request, preventing pool exhaustion in production.
- Test suites can inject transaction-scoped or in-memory test sessions without patching module globals.

Negative:
- Developers must learn the generator-based `Depends()` pattern, which is less intuitive than creating a session inline.
- All route handlers that need a session must declare it as a typed parameter, adding verbosity in large codebases.

## Alternatives

- Use a `contextvars`-based session pattern (rejected)
  Rejected because: Context-variable session management is more complex, does not benefit from FastAPI's automatic dependency lifecycle, and makes test overrides harder to implement cleanly.
  When valid: In non-FastAPI async frameworks where dependency injection is unavailable.

## Risks

- Developers may accidentally create sessions inside utility functions called from handlers, bypassing the DI lifecycle.
  Mitigation: Establish a convention of passing the session as an explicit parameter to all service and utility functions rather than creating it internally; enforce in code review.