# Apply Authentication Dependencies at the APIRouter Level, Not Per-Endpoint

Status: accepted
Date: 2026-03-31
Deciders: ADR Bank Curation

## Context

- Declaring `Depends(verify_token)` on every individual route function is error-prone.
- New routes added to a router can silently become unauthenticated when the dependency annotation is forgotten.
- FastAPI's `APIRouter` supports router-level `dependencies` that apply automatically to every registered route.
- Router-level dependencies enforce authentication as a structural constraint rather than a per-function opt-in annotation.

## Problem Statement

Per-endpoint authentication dependency declarations create a class of silent security bugs: new routes added to an authenticated router are unintentionally exposed without authentication when the developer forgets the annotation. Applying auth at the router level makes protection a structural property of the route group that cannot be accidentally omitted.

## Decision

1. MUST: Apply authentication dependencies via `dependencies=[Depends(...)]` on the `APIRouter` constructor, not on individual route function signatures.
2. MUST: Use separate `APIRouter` instances for public and authenticated route groups.

## Policy Block

- MUST apply authentication dependencies via `dependencies=[Depends(...)]` on the `APIRouter` constructor, not on individual route function signatures.
- MUST use separate `APIRouter` instances for public and authenticated route groups.

In scope:
- FastAPI `APIRouter` configuration for authenticated API route groups.
- Separation of public and protected route namespaces at the router level.
- Router-level dependency application at router construction time or via `app.include_router(..., dependencies=[...])`.

Out of scope:
- Fine-grained per-endpoint authorization checks such as resource ownership or role-based access — these still belong in handler logic or dedicated per-endpoint dependencies.
- Authentication middleware patterns that operate outside FastAPI's DI system.
- WebSocket authentication, which has a different lifecycle from HTTP route handlers.

Exceptions:
- EXC-001: When an individual route within an authenticated router must be publicly accessible, it may declare its own dependency override, but this exception must be explicitly documented with an inline comment.

## Rationale

- Router-level dependencies are structural — they are inherited by every route added to the router and cannot be accidentally omitted when a new endpoint is added.
- Separating public and authenticated routers makes the security boundary visible and auditable in the application's routing structure, rather than scattered across hundreds of function signatures.

## Consequences

Positive:
- New routes added to an authenticated router inherit authentication automatically, eliminating the forgotten-dependency bug class.
- The security boundary between public and protected routes is explicit and auditable in one location per router.

Negative:
- Router-level dependencies do not inject resolved values into handler parameters; handlers that need the resolved auth value (e.g., the current user object) must still declare the dependency in their function signature.
- Separating into multiple routers adds minor structural overhead that may feel unnecessary for small applications.

## Alternatives

- Apply authentication as ASGI middleware (rejected)
  Rejected because: ASGI middleware cannot easily differentiate public vs. authenticated routes as declared in FastAPI's router structure, and does not participate in FastAPI's dependency injection lifecycle or benefit from `app.dependency_overrides` in tests.
  When valid: For blanket authentication across all routes with no public exceptions and no need for the resolved identity in handler logic.

## Risks

- Developers may add a per-route `dependencies=[]` override to bypass router-level auth without recognizing the security implication.
  Mitigation: Document the pattern explicitly in contributing guidelines; consider a lint rule or code review checklist item that flags per-route auth dependency declarations on routers already protected at the router level.