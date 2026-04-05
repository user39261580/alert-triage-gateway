# Use Return Type Annotations for Response Schemas; Reserve response_model= for Type Divergence

Status: accepted
Date: 2026-03-31
Deciders: ADR Bank Curation

## Context

- Without any response model, FastAPI serializes the raw return value with no field filtering.
- Returning an ORM object that includes password or internal fields silently exposes them.
- FastAPI emits no warning when no response schema is configured.
- FastAPI can infer the response model from the function's return type annotation, making explicit response_model= redundant in most cases.

## Problem Statement

Without a declared response schema, FastAPI silently serializes all fields of returned objects — including sensitive internal fields like passwords — with no warning. Developers need a clear, consistent pattern for declaring response schemas that minimizes redundancy while ensuring sensitive data is never accidentally exposed.

## Decision

1. MUST: Annotate route return types (-> UserOut) to let FastAPI infer the response model automatically.
2. SHOULD: Use response_model= only when the function return type and the desired output schema differ.
3. SHOULD: Use response_model_exclude_unset=True on PATCH endpoints to omit fields the client did not provide.

## Policy Block

- MUST annotate route function return types (-> SchemaOut) to let FastAPI infer the response model automatically.
- SHOULD use response_model= only when the function return type and the desired output schema differ (e.g., returning an ORM object that must be filtered to a public schema).
- SHOULD add response_model_exclude_unset=True on PATCH endpoints to omit fields the client did not provide.

In scope:
- All FastAPI route handler functions
- Response schema declaration via return type annotations and response_model=
- Pydantic response models used for field filtering and serialization
- PATCH endpoint response configuration

Out of scope:
- Request body validation and input schemas
- WebSocket endpoint response handling
- Streaming responses (StreamingResponse, EventSourceResponse)
- OpenAPI schema customization beyond response models

Exceptions:
- EXC-001: When returning an ORM model that contains sensitive fields (e.g., hashed_password), response_model=PublicSchema must be used even if the return type could be annotated, to ensure filtering is explicit and visible in the decorator.

## Rationale

- Return type annotations keep the response schema co-located with the function signature, reducing duplication and making the contract immediately visible to developers.
- Reserving response_model= for divergence cases makes its presence a signal that intentional type transformation is occurring, improving code readability.
- FastAPI's automatic inference from return types produces identical OpenAPI documentation and runtime filtering as explicit response_model=.

## Consequences

Positive:
- Reduced boilerplate: response schema is declared once in the function signature instead of repeated in the decorator.
- Clearer intent: the presence of response_model= signals that the return type and output schema intentionally differ.
- Sensitive fields are always filtered through a declared Pydantic schema.

Negative:
- Developers must understand when return type inference is insufficient and response_model= is required, which adds a decision point.
- ORM objects returned without any schema annotation still silently expose all fields — this ADR does not add a lint guard.

## Alternatives

- Always use response_model= on every route, ignoring return type inference (rejected)
  Rejected because: Creates redundancy between the decorator and the return type annotation, and the duplicated type can drift out of sync.
  When valid: In codebases where return type annotations are not consistently used or enforced by linting.

## Risks

- A developer returns an ORM object with a correct return type annotation (-> UserORM) but UserORM contains sensitive fields, believing the annotation filters output. FastAPI does not filter fields when the return type matches the actual returned object.
  Mitigation: Enforce a lint rule or code review check that route return types must be Pydantic response schemas, never ORM models.