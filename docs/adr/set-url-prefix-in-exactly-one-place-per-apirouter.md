# Set URL Prefix in Exactly One Place per APIRouter

Status: accepted
Date: 2026-03-31
Deciders: ADR Bank Curation

## Context

- Setting prefix= on both APIRouter(prefix='/users') and include_router(router, prefix='/users') doubles the path at runtime.
- The doubled path (e.g., /users/users/{id}) produces no startup error or warning from FastAPI.
- This silent failure means incorrect routes are only discovered at runtime when HTTP requests return 404 or hit unexpected endpoints.
- FastAPI does not validate or deduplicate prefixes across router definition and inclusion.

## Problem Statement

FastAPI silently concatenates prefix values from both APIRouter() and include_router() without warning, producing doubled URL paths (e.g., /users/users/{id}) that are only discovered at runtime through unexpected 404 errors or misrouted requests.

## Decision

1. MUST: Set prefix= either on APIRouter() or on include_router(), never on both for the same router.
2. SHOULD: Use include_router(prefix='/v1') for API versioning and APIRouter(prefix='/users') for resource grouping.
3. SHOULD: Verify routes after startup by inspecting /openapi.json paths or calling app.url_path_for().
4. MAY: Apply tags= on include_router to extend or override tags defined on the router itself.

## Policy Block

- MUST set prefix= either on APIRouter() or on include_router(), never on both for the same router.
- SHOULD use include_router(prefix=) for API versioning and APIRouter(prefix=) for resource grouping.
- SHOULD verify routes after startup by inspecting /openapi.json paths or calling app.url_path_for().
- MAY apply tags= on include_router to extend or override tags defined on the router.

In scope:
- FastAPI APIRouter prefix configuration
- FastAPI include_router() prefix and tags parameters
- URL path construction and route registration in FastAPI applications

Out of scope:
- Path parameter validation and type coercion
- Middleware ordering and configuration
- Non-FastAPI routing frameworks (Flask blueprints, Django URL conf)

Exceptions:
- None currently documented.

## Rationale

- A single source of truth for URL prefixes eliminates the silent path-doubling bug that FastAPI does not warn about.
- Separating versioning (include_router) from resource grouping (APIRouter) creates a clear, maintainable routing hierarchy.
- Inspecting /openapi.json after startup provides a fast verification loop that catches routing errors before they reach users.

## Consequences

Positive:
- URL paths are predictable and match developer expectations without runtime debugging.
- The routing hierarchy is easier to understand when prefixes are set in a consistent location.
- OpenAPI documentation accurately reflects the actual API surface.

Negative:
- Teams must establish and enforce a convention for which location (router vs. include) owns the prefix, adding a coordination cost.
- Refactoring existing routers that set prefix in both places requires careful audit to avoid breaking clients.

## Alternatives

- Always set prefix on APIRouter() and never on include_router() (rejected)
  Rejected because: This prevents API versioning at the include site, forcing version prefixes into each router definition and reducing reusability across API versions.
  When valid: In small applications with a single API version where router reuse is not needed.

## Risks

- A developer unfamiliar with the convention adds prefix in the wrong location, reintroducing the doubled-path bug.
  Mitigation: Add a startup check or test that inspects registered routes via app.routes and asserts no path contains consecutive duplicate segments.