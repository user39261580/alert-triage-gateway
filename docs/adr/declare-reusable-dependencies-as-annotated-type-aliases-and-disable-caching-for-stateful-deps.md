# Declare Reusable Dependencies as Annotated Type Aliases and Disable Caching for Stateful Deps

Status: accepted
Date: 2026-03-31
Deciders: ADR Bank Curation

## Context

- FastAPI caches dependency results per-request by default.
- A dependency called twice in the same request silently returns the first result.
- This caching behavior breaks audit loggers, nonce generators, or any per-call operation that must execute fresh each time.
- Inline `Depends()` in default arguments leads to repetition and inconsistent dependency declarations across routes.

## Problem Statement

Without declaring dependencies as reusable type aliases and disabling caching for stateful dependencies, developers silently receive stale cached results for operations that must run independently per call site, leading to broken audit trails, duplicate nonces, and subtle per-request bugs that are invisible in unit tests.

## Decision

1. MUST: Declare reusable dependencies as `Annotated` type aliases rather than inline `Depends()` default arguments.
2. MUST: Pass `use_cache=False` to `Depends()` for any dependency that must not be shared across call sites within a request.
3. SHOULD: Use `try/finally` in yield dependencies to guarantee cleanup even when an exception is raised.

## Policy Block

- MUST declare reusable dependencies as `Annotated` type aliases rather than inline `Depends()` default arguments.
- MUST pass `use_cache=False` to `Depends()` for any dependency that must not be shared across call sites within a request.
- SHOULD use `try/finally` in yield dependencies to guarantee cleanup even when an exception is raised.

In scope:
- FastAPI dependency injection patterns and `Depends()` usage
- Per-request dependency caching behavior
- `Annotated` type alias declarations for dependencies
- Yield-based dependency lifecycle management

Out of scope:
- Database session or connection pool configuration
- Authentication/authorization logic within dependencies
- Testing strategies for dependency mocking
- Middleware-based request processing

Exceptions:
- EXC-001: Inline `Depends()` in default arguments is acceptable for one-off route-specific dependencies that are not reused elsewhere.

## Rationale

- `Annotated` type aliases centralize the dependency declaration, making it reusable, consistent, and easier to update across all routes.
- Explicitly disabling caching for stateful dependencies prevents silent data corruption from FastAPI's default per-request caching.
- Yield dependencies with `try/finally` ensure resource cleanup happens regardless of exceptions, preventing resource leaks.

## Consequences

Positive:
- Dependencies are declared once and reused consistently across all routes without repetition.
- Stateful dependencies (audit loggers, nonce generators) execute correctly on every call site.
- Resource cleanup is guaranteed even during exception handling.

Negative:
- Developers must understand FastAPI's caching semantics to know when `use_cache=False` is needed, adding cognitive overhead.
- Type alias indirection may be less immediately obvious than inline `Depends()` for developers new to the codebase.

## Alternatives

- Inline `Depends()` in every route function signature (rejected)
  Rejected because: Leads to repetition, inconsistency, and makes it easy to forget `use_cache=False` on stateful dependencies.
  When valid: For truly one-off dependencies used in a single route.

- Middleware-based dependency injection (rejected)
  Rejected because: Middleware operates at a different lifecycle stage and cannot provide per-route type-safe dependency resolution.
  When valid: For cross-cutting concerns like request logging that apply to all routes uniformly.

## Risks

- A developer forgets `use_cache=False` on a new stateful dependency, reintroducing the silent caching bug.
  Mitigation: Document which dependency categories require `use_cache=False` and add a code review checklist item for new dependencies.

- Over-applying `use_cache=False` to dependencies that are safe to cache increases per-request overhead.
  Mitigation: Only disable caching for dependencies with observable side effects; pure data-fetching dependencies should retain caching.