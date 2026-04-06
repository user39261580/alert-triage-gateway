# Define Domain Exceptions Without FastAPI Imports and Register Handlers at the App Level

Status: accepted
Date: 2026-03-31
Deciders: ADR Bank Curation

## Context

- FastAPI's `HTTPException` and Starlette's `HTTPException` are distinct classes with different import paths.
- A handler registered for FastAPI's `HTTPException` does not intercept Starlette's internally raised 404 (route not found) and 405 (method not allowed) errors.
- Unhandled Starlette exceptions bypass custom error formatting and return Starlette's default HTML error response, breaking JSON API contracts.
- Coupling domain exceptions to FastAPI imports makes the service layer untestable without the web framework.

## Problem Statement

Without separating domain exceptions from FastAPI imports and registering handlers for both FastAPI and Starlette exception classes, applications return inconsistent error formats — JSON for application errors but HTML for framework-level 404/405 errors — breaking API clients.

## Decision

1. MUST: Define domain exceptions as plain Python classes in the service layer with no FastAPI imports.
2. MUST: Register exception handlers with `@app.exception_handler()` in `main.py`, not inside routers or route functions.
3. MUST: Register a handler on `starlette.exceptions.HTTPException` to catch route-not-found and method-not-allowed errors.
4. SHOULD: Override the default 422 format by registering a handler for `RequestValidationError` from `fastapi.exceptions`.

## Policy Block

- MUST define domain exceptions as plain Python classes with no FastAPI imports.
- MUST register exception handlers with `@app.exception_handler()` in the application entry point (`main.py`).
- MUST register a handler on `starlette.exceptions.HTTPException` to intercept 404 and 405 errors.
- MUST NOT register exception handlers inside routers or individual route functions.
- SHOULD override the default 422 `RequestValidationError` handler to return a consistent JSON error format.
- SHOULD return `JSONResponse` from all exception handlers to maintain a uniform API error contract.

In scope:
- FastAPI and Starlette exception handler registration.
- Domain exception class design and placement.
- Error response format consistency across all HTTP status codes.

Out of scope:
- Business logic validation (e.g., which conditions raise `NotFoundError` vs `ForbiddenError`).
- Logging and error reporting configuration (Sentry, structured logging).
- GraphQL or WebSocket error handling.

Exceptions:
- EXC-001: Router-scoped exception handlers may be used for route-group-specific error transformations (e.g., a legacy API compatibility layer) if documented with an inline comment.

## Rationale

- Plain Python exceptions decouple the service layer from the web framework, enabling reuse in CLI tools, background workers, and tests without importing FastAPI.
- Centralized handler registration in `main.py` provides a single location to audit error formatting, reducing the risk of inconsistent responses.
- Registering on Starlette's `HTTPException` ensures that framework-level errors (404, 405) are formatted identically to application errors.

## Consequences

Positive:
- All API error responses use a consistent JSON format regardless of whether the error originates from application code or the framework.
- The service layer is framework-agnostic and can be tested without starting a FastAPI application.
- Error formatting logic is centralized and auditable in a single file.

Negative:
- Developers must understand the distinction between FastAPI's and Starlette's `HTTPException` classes, which is a non-obvious framework detail.
- Adding a new domain exception requires updating both the exception module and the handler registration in `main.py`.

## Alternatives

- Raise `fastapi.HTTPException` directly from service layer code. (rejected)
  Rejected because: This couples the service layer to FastAPI, making it untestable without the framework and unusable in non-web contexts.
  When valid: Acceptable in small, single-purpose FastAPI applications where the service layer will never be reused outside the web context.

## Risks

- A new exception class added to the domain layer without a corresponding handler registration will result in an unhandled 500 error with a framework-default response.
  Mitigation: Add a catch-all `Exception` handler that returns a generic 500 JSON response, and log unhandled exception types for detection.