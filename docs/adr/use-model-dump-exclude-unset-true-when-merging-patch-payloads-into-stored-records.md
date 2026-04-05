# Use model_dump(exclude_unset=True) When Merging PATCH Payloads into Stored Records

Status: accepted
Date: 2026-03-31
Deciders: ADR Bank Curation

## Context

- Pydantic populates omitted optional fields with their default values when parsing a request body.
- Without `exclude_unset=True`, a PATCH request that omits a field overwrites that field with its Pydantic default.
- This silently destroys existing data stored in the record without raising any error.
- This is the most common correctness bug in FastAPI PATCH endpoint implementations.

## Problem Statement

When merging a PATCH payload into a stored record, calling `.model_dump()` without `exclude_unset=True` causes omitted fields to overwrite existing data with Pydantic defaults, silently corrupting stored records. Following this ADR prevents data loss on partial updates.

## Decision

1. MUST: Call `patch_body.model_dump(exclude_unset=True)` when merging a PATCH payload into a stored record.
2. MUST: Define a separate request schema for PATCH endpoints with all fields typed as `Optional[T]` with `None` defaults — never reuse the POST create schema.

## Policy Block

- MUST call `patch_body.model_dump(exclude_unset=True)` when merging a PATCH payload into a stored record.
- MUST define a separate request schema for PATCH endpoints with all fields typed as `Optional[T]` with `None` defaults — never reuse the POST create schema.

In scope:
- FastAPI PATCH endpoint handlers that update existing database records.
- Pydantic v2 model serialization in the context of partial updates.
- Merging partial payloads with stored ORM or dictionary records using the `stored_data | patch_body.model_dump(exclude_unset=True)` pattern.

Out of scope:
- PUT endpoints where full replacement semantics are intentional.
- POST create endpoints where all required fields must be present.
- Non-Pydantic request parsing approaches.

Exceptions:
- EXC-001: None currently documented.

## Rationale

- Pydantic's default-population behavior is correct for schema validation but incorrect for merge semantics — `exclude_unset=True` bridges this mismatch by serializing only fields the caller explicitly sent.
- Using a dedicated PATCH schema with all-optional fields makes the contract explicit: callers are not required to send fields they do not intend to change, and the schema enforces that intent at the type level.

## Consequences

Positive:
- Existing record fields not included in the PATCH payload are preserved without additional guard logic in handler code.
- The merge pattern (`stored_data | patch_body.model_dump(exclude_unset=True)`) is concise, readable, and auditable.

Negative:
- Requires maintaining two separate schemas (create and update) per resource, increasing boilerplate.
- Developers unfamiliar with the pattern may inadvertently call `.model_dump()` without `exclude_unset=True` and silently introduce the bug.

## Alternatives

- Use PUT semantics for all updates (rejected)
  Rejected because: Requiring a full resource representation on every update is impractical for large objects and creates a worse API contract for clients who must first fetch the full record before updating a single field.
  When valid: When the API explicitly guarantees and documents full replacement semantics.

## Risks

- A developer may call `.model_dump()` without `exclude_unset=True` and bypass this rule without a build-time error.
  Mitigation: Enforce via code review checklist and add integration tests that send partial PATCH payloads asserting omitted fields remain unchanged in the stored record.