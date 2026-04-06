# Verify JWTs Explicitly in a Dependency — OAuth2PasswordBearer Only Extracts the Token

Status: accepted
Date: 2026-03-31
Deciders: ADR Bank Curation

## Context

- `OAuth2PasswordBearer` in FastAPI returns the raw bearer token string but performs no signature verification, expiry check, or audience validation.
- A route depending solely on `OAuth2PasswordBearer` accepts any non-empty `Authorization: Bearer <token>` header, providing no actual authentication.
- The Python JWT ecosystem includes multiple libraries with different security postures: PyJWT (maintained), python-jose (unmaintained since 2022), and passlib (known vulnerabilities).
- The HTTP specification requires a `WWW-Authenticate: Bearer` header in 401 responses to inform clients of the expected authentication scheme.

## Problem Statement

Without explicit JWT verification in a dedicated dependency, routes using `OAuth2PasswordBearer` appear authenticated but accept any token string, leaving the application completely unprotected against unauthorized access.

## Decision

1. MUST: Always decode and verify the JWT in a `get_current_user` dependency using `jwt.decode()`, not `OAuth2PasswordBearer` alone.
2. MUST: Use PyJWT for JWT handling — avoid python-jose (unmaintained) and passlib (known security vulnerabilities).
3. MUST: Return `WWW-Authenticate: Bearer` in the headers of every 401 Unauthorized response.
4. MUST: Store the JWT secret key in an environment variable, never hardcoded in source.
5. SHOULD: Specify the `algorithms` parameter explicitly in `jwt.decode()` to prevent algorithm confusion attacks.

## Policy Block

- MUST decode and verify JWTs in a `get_current_user` dependency using `jwt.decode()`.
- MUST use PyJWT (`pyjwt`) as the JWT library.
- MUST NOT use python-jose or passlib for JWT operations.
- MUST return `WWW-Authenticate: Bearer` header in all 401 responses.
- MUST store `SECRET_KEY` in an environment variable.
- MUST NOT hardcode secret keys in source code.
- SHOULD specify `algorithms=['HS256']` (or the appropriate algorithm) explicitly in `jwt.decode()`.
- SHOULD raise `HTTPException(status_code=401, headers={'WWW-Authenticate': 'Bearer'})` on any decode failure.

In scope:
- JWT verification in FastAPI dependency injection.
- JWT library selection for Python applications.
- Authentication error response formatting.
- Secret key management for JWT signing.

Out of scope:
- OAuth2 authorization server implementation (token issuance, refresh tokens).
- Role-based access control and permission checking beyond authentication.
- API key authentication or other non-JWT authentication schemes.
- Frontend token storage and refresh strategies.

Exceptions:
- EXC-001: Public endpoints that intentionally allow unauthenticated access do not require the `get_current_user` dependency.

## Rationale

- `OAuth2PasswordBearer` is a token extraction utility, not an authentication mechanism — its name is misleading and leads developers to assume it provides security.
- PyJWT is actively maintained and has a focused scope (JWT only), reducing supply chain risk compared to multi-purpose libraries.
- Explicit algorithm specification prevents algorithm confusion attacks where an attacker crafts a token using an unexpected algorithm (e.g., `none` or `HS256` when `RS256` is expected).

## Consequences

Positive:
- All protected routes are genuinely authenticated, with token signature and expiry verified on every request.
- Using a single, maintained JWT library reduces security vulnerability surface.
- `WWW-Authenticate` headers enable proper browser and client behavior for authentication challenges.

Negative:
- Every route that needs authentication must depend on `get_current_user`, adding boilerplate to route signatures.
- Secret key rotation requires coordination between the token issuer and all verifying services.

## Alternatives

- Use python-jose for JWT handling, which provides a broader cryptographic API. (rejected)
  Rejected because: python-jose has been unmaintained since 2022, and known CVEs remain unpatched. Its broader scope increases attack surface unnecessarily.
  When valid: Only if the application requires JWE (encrypted JWTs) and no other maintained library supports it.

- Rely on an API gateway or reverse proxy for JWT verification. (rejected)
  Rejected because: Defense in depth requires application-level verification; gateway-only verification creates a single point of failure and makes local development harder.
  When valid: As an additional layer of verification in production, not as a replacement for application-level checks.

## Risks

- A misconfigured `algorithms` parameter (e.g., allowing `none`) could bypass signature verification entirely.
  Mitigation: Always specify a single expected algorithm explicitly and never include `none` in the algorithms list. Add a startup assertion that validates the algorithm configuration.