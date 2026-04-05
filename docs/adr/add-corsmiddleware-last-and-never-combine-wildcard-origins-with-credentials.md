# Add CORSMiddleware Last and Never Combine Wildcard Origins with Credentials

Status: accepted
Date: 2026-03-31
Deciders: ADR Bank Curation

## Context

- Starlette applies middleware in LIFO (last-in, first-out) order — the last `add_middleware` call runs first (outermost layer).
- If authentication middleware is added after CORS middleware, it becomes the outermost layer and rejects browser OPTIONS preflight requests with 401 before CORS headers can be set.
- Combining `allow_origins=['*']` with `allow_credentials=True` violates the CORS specification (the browser ignores the wildcard when credentials are present).
- Starlette raises no startup error for the invalid wildcard-plus-credentials combination, making it a silent misconfiguration.

## Problem Statement

Without placing CORSMiddleware as the outermost ASGI layer and avoiding the wildcard-plus-credentials combination, browsers will either fail preflight requests with 401 errors or silently ignore CORS headers, breaking cross-origin API access for frontend applications.

## Decision

1. MUST: Call `app.add_middleware(CORSMiddleware, ...)` after all other `add_middleware` calls so it becomes the outermost ASGI layer.
2. MUST: Never combine `allow_origins=['*']` with `allow_credentials=True` — enumerate allowed origins explicitly when credentials are required.
3. SHOULD: Use `allow_origin_regex` for local development with variable ports instead of a wildcard origin.

## Policy Block

- MUST call `app.add_middleware(CORSMiddleware, ...)` after all other `add_middleware` calls.
- MUST NOT combine `allow_origins=['*']` with `allow_credentials=True`.
- MUST enumerate allowed origins explicitly when `allow_credentials=True` is set.
- SHOULD use `allow_origin_regex=r'https?://localhost:\d+'` for local development with variable ports.
- SHOULD document the required middleware ordering in the application's startup module.

In scope:
- Starlette and FastAPI `CORSMiddleware` configuration.
- Middleware ordering in ASGI applications using `add_middleware`.
- CORS origin configuration for credentialed requests.

Out of scope:
- CORS configuration at the reverse proxy or CDN level (Nginx, Cloudflare).
- Non-browser API clients that do not send preflight requests.
- WebSocket CORS handling (governed by different browser policies).

Exceptions:
- EXC-001: Public APIs that never use cookies or Authorization headers may use `allow_origins=['*']` without `allow_credentials=True`.

## Rationale

- LIFO middleware ordering is a Starlette implementation detail that is not immediately obvious; documenting the required order prevents recurring misconfiguration.
- The CORS spec explicitly forbids wildcard origins with credentials, and browsers enforce this silently — no error is surfaced to the developer.
- Explicit origin enumeration is more secure and makes the list of trusted frontends auditable.

## Consequences

Positive:
- Browser preflight requests succeed reliably, eliminating a common class of "works in Postman, fails in browser" bugs.
- CORS configuration is spec-compliant and behaves consistently across browsers.
- Explicit origin lists provide a clear audit trail of trusted frontends.

Negative:
- Adding new frontend origins requires updating the CORS configuration and redeploying the backend.
- Developers must understand Starlette's LIFO middleware ordering, which is counterintuitive compared to frameworks that use FIFO ordering.

## Alternatives

- Configure CORS at the reverse proxy layer (Nginx, Cloudflare) instead of in the application. (rejected)
  Rejected because: Application-level CORS is easier to test, version-control, and keep in sync with route changes. Proxy-level CORS can drift from application expectations.
  When valid: Acceptable when the application is behind an API gateway that centrally manages CORS for multiple services.

## Risks

- Environment-specific origin lists (dev, staging, prod) may diverge, causing CORS failures in non-production environments.
  Mitigation: Load allowed origins from environment variables and validate them at startup.