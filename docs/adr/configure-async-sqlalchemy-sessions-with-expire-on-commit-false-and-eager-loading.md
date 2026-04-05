# Configure Async SQLAlchemy Sessions with expire_on_commit=False and Eager Loading

Status: accepted
Date: 2026-03-31
Deciders: ADR Bank Curation

## Context

- SQLAlchemy defaults to `expire_on_commit=True`, which expires all loaded attributes after `await session.commit()`.
- In async context, accessing expired attributes triggers lazy loading, which issues synchronous SQL.
- Synchronous SQL in async mode raises `MissingGreenlet` because the async driver cannot execute blocking I/O on the event loop.
- This failure mode is not caught at commit time — it surfaces only when application code accesses an attribute after commit, making it difficult to diagnose.

## Problem Statement

Without setting `expire_on_commit=False` and using eager loading, async SQLAlchemy applications crash with `MissingGreenlet` errors whenever they access model attributes after a commit, because expired attributes trigger synchronous lazy loading that the async driver forbids.

## Decision

1. MUST: Create `async_sessionmaker` with `expire_on_commit=False`.
2. MUST: Load all required relationships using `selectinload` or `joinedload` inside the query — never access relationship attributes after the session closes.
3. SHOULD: Commit inside route handlers, not inside CRUD functions, to keep one transaction per request.

## Policy Block

- MUST create `async_sessionmaker` with `expire_on_commit=False`.
- MUST load all required relationships using `selectinload` or `joinedload` inside the query.
- MUST NOT access relationship attributes after the session closes without prior eager loading.
- SHOULD commit inside route handlers, not inside CRUD functions, to maintain one transaction per request.
- SHOULD use `selectinload` as the default eager loading strategy for collections and `joinedload` for single-valued relationships.

In scope:
- All async SQLAlchemy session factory configuration (`async_sessionmaker`, `AsyncSession`).
- Relationship loading strategies in async queries (`selectinload`, `joinedload`, `subqueryload`).
- Transaction boundary placement in async web applications.

Out of scope:
- Synchronous SQLAlchemy session configuration (lazy loading works correctly in sync mode).
- Connection pool tuning and engine-level settings.
- Database migration tooling (Alembic configuration).

Exceptions:
- EXC-001: Background tasks that create their own sessions may use `expire_on_commit=True` if all attribute access occurs within the session scope and before commit.

## Rationale

- `expire_on_commit=False` is the only safe default for async sessions because the async driver cannot fall back to synchronous lazy loading.
- Eager loading makes data dependencies explicit in the query, preventing N+1 query problems and making performance characteristics visible at the query site.
- Committing at the handler level ensures a single transaction boundary per request, simplifying rollback logic and error handling.

## Consequences

Positive:
- Eliminates `MissingGreenlet` errors caused by post-commit attribute access.
- Makes relationship loading explicit, preventing hidden N+1 queries.
- Simplifies debugging by keeping transaction boundaries visible at the handler level.

Negative:
- `expire_on_commit=False` means in-memory objects may hold stale data if the database is modified by another process between commit and subsequent reads within the same session.
- Developers must remember to add eager loading options for every relationship they intend to access, increasing query verbosity.

## Alternatives

- Use synchronous SQLAlchemy with `run_in_executor` for all database operations. (rejected)
  Rejected because: This negates the performance benefits of async I/O and adds unnecessary complexity with thread pool management.
  When valid: Acceptable in codebases where async adoption is partial and the database layer is isolated behind a synchronous repository interface.

## Risks

- Stale data from `expire_on_commit=False` could cause logic errors if the same session is reused across multiple requests or long-lived operations.
  Mitigation: Use short-lived sessions scoped to a single request via dependency injection, and call `session.refresh(obj)` when fresh data is explicitly needed.