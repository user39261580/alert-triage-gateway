# Set response_model_exclude_unset=True on Endpoints Returning Models with Many Optional Fields

Status: accepted
Date: 2026-03-31
Deciders: ADR Bank Curation

## Context

- FastAPI serializes every field declared in response_model by default, including Optional fields that were never set.
- Clients receive null for unset Optional fields and cannot distinguish "field is null" from "field was not provided."
- This breaks partial-response semantics when clients rely on field presence to determine availability.
- Sending null for all unset Optional fields inflates payload size on models with many optional fields.

## Problem Statement

Without response_model_exclude_unset=True, FastAPI includes every declared Optional field in responses as null, making it impossible for clients to distinguish intentionally null values from absent fields and unnecessarily increasing payload size.

## Decision

1. MUST: Set response_model_exclude_unset=True on endpoints whose response_model contains multiple Optional fields.
2. MUST: Never use ORM model classes directly as response_model — define dedicated Pydantic response schemas.
3. SHOULD: Use response_model_exclude={'field'} to strip sensitive fields from a specific endpoint's response.
4. SHOULD: Prefer defining sensitive field exclusions in the response schema itself via Field(exclude=True) over per-endpoint response_model_exclude.

## Policy Block

- MUST set response_model_exclude_unset=True on endpoints whose response_model contains multiple Optional fields
- MUST NOT use ORM model classes directly as response_model — define dedicated Pydantic response schemas
- SHOULD use response_model_exclude to strip sensitive fields from specific endpoint responses
- SHOULD prefer Field(exclude=True) in response schemas over per-endpoint exclusions for sensitive fields

In scope:
- FastAPI endpoint decorator configuration for response serialization
- Pydantic response schema definitions for API endpoints
- Handling of Optional fields in response models
- Sensitive field exclusion strategies

Out of scope:
- Request body validation and deserialization
- Database ORM model definitions
- Non-FastAPI serialization frameworks
- WebSocket or streaming response endpoints

Exceptions:
- EXC-001: Endpoints where the client explicitly requires null to be serialized for all Optional fields may omit response_model_exclude_unset=True, but this must be documented in the endpoint docstring.

## Rationale

- Clients interacting with partial-update APIs need to distinguish "field not provided" from "field is null"; including unset fields as null destroys this distinction.
- Excluding unset fields reduces payload size for models with many optional fields, improving network efficiency for high-traffic endpoints.
- Dedicated Pydantic response schemas decouple internal ORM structure from the public API contract, preventing accidental field exposure.

## Consequences

Positive:
- Clients receive clean partial responses containing only fields that were explicitly set, enabling reliable field-presence checks.
- Payload sizes decrease for responses with many optional fields, reducing bandwidth and serialization overhead.

Negative:
- Developers must remember to add response_model_exclude_unset=True per endpoint; forgetting it causes subtle client-side bugs that are hard to detect.
- Requiring separate Pydantic response schemas increases the number of model classes to maintain alongside ORM models.

## Alternatives

- Serialize all fields including unset ones (default FastAPI behavior) (rejected)
  Rejected because: Clients cannot determine whether a null value was explicitly set or simply not provided, breaking partial-response semantics.
  When valid: Simple CRUD APIs where all fields are always present and null has a single unambiguous meaning.

## Risks

- A developer adds a new Optional field to the response schema but expects it to appear in responses even when unset; the field is silently omitted.
  Mitigation: Document the exclude_unset behavior in the schema's docstring and include integration tests asserting field presence for both set and unset scenarios.