# Cache Settings with @lru_cache and Expose via Depends for Testability

Status: accepted
Date: 2026-03-31
Deciders: ADR Bank Curation

## Context

- Without `@lru_cache`, pydantic-settings re-reads and re-parses the `.env` file on every request, adding unnecessary I/O overhead.
- Without `Depends`, tests must monkeypatch environment variables rather than using `app.dependency_overrides` for clean, isolated overrides.
- Instantiating `Settings()` at module level in business logic couples configuration loading to import time, making testing and reconfiguration difficult.

## Problem Statement

Repeated `Settings()` instantiation causes redundant `.env` file parsing on every request, and without dependency injection, test isolation requires brittle monkeypatching of environment variables instead of clean dependency overrides.

## Decision

1. MUST: Wrap the `Settings()` constructor in a `@lru_cache` function and expose it as a FastAPI dependency.
2. MUST: Never instantiate `Settings()` at module level in business logic or router modules.
3. MUST: Inject settings via `Annotated[Settings, Depends(get_settings)]` in route handlers.
4. MUST: Call `get_settings.cache_clear()` in test teardown to prevent settings state leaking between tests.
5. SHOULD: Override settings in tests via `app.dependency_overrides[get_settings]` rather than monkeypatching environment variables.

## Policy Block

- MUST wrap the `Settings()` constructor in a `@lru_cache` function and expose it as a FastAPI dependency.
- MUST never instantiate `Settings()` at module level in business logic or router modules.
- MUST inject settings in routes via `Annotated[Settings, Depends(get_settings)]`.
- MUST call `get_settings.cache_clear()` in test teardown to prevent settings state leaking between tests.
- SHOULD override settings in tests via `app.dependency_overrides[get_settings]`.

In scope:
- FastAPI applications using pydantic-settings for configuration
- Route handler dependency injection of settings objects
- Test isolation patterns for configuration overrides
- Cache lifecycle management for settings singletons

Out of scope:
- Non-FastAPI Python applications or CLI tools
- Runtime configuration reloading beyond cache clearing
- Secrets management and vault integration
- Environment variable validation schemas

Exceptions:
- EXC-001: Module-level `Settings()` instantiation is acceptable in the settings definition module itself (e.g., `config.py`) where the `@lru_cache` wrapper is defined.

## Rationale

- `@lru_cache` ensures the `.env` file is parsed exactly once per process, eliminating redundant I/O on every request.
- Exposing settings via `Depends` leverages FastAPI's built-in `dependency_overrides` mechanism, making test isolation trivial without monkeypatching.
- Keeping `Settings()` out of module-level scope prevents import-time side effects and makes the dependency graph explicit.

## Consequences

Positive:
- Eliminates per-request `.env` file parsing overhead, improving throughput.
- Tests gain clean, isolated configuration overrides via `app.dependency_overrides` without touching environment variables.
- Configuration dependencies become explicit and visible in function signatures.

Negative:
- Developers must remember to call `cache_clear()` in test teardown; forgetting causes subtle cross-test state leakage.
- Adds a small layer of indirection compared to direct `Settings()` instantiation.

## Alternatives

- Instantiate `Settings()` as a module-level singleton without `@lru_cache` or `Depends` (rejected)
  Rejected because: Module-level instantiation couples configuration to import time and forces tests to use monkeypatching, which is fragile and non-isolated.
  When valid: Simple scripts or CLI tools where testability and per-request overhead are not concerns.

## Risks

- Cached settings persist stale values if environment variables change at runtime (e.g., during hot-reload in development).
  Mitigation: Call `get_settings.cache_clear()` explicitly when environment changes are expected, or use a TTL-based cache for development environments.