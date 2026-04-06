# Replace orm_mode = True with ConfigDict(from_attributes=True) for ORM Response Schemas

Status: accepted
Date: 2026-03-31
Deciders: ADR Bank Curation

## Context

- Pydantic v2 removed `class Config: orm_mode = True` from its API.
- Without migration, `response_model` serialization of ORM instances silently returns empty or incorrect data, or raises `ValidationError` at runtime.
- No build-time error is produced; the failure only surfaces when the endpoint is called.
- `Schema.from_orm(instance)` is also removed in Pydantic v2 and must be replaced with `Schema.model_validate(instance)`.

## Problem Statement

Pydantic v2 no longer supports the `orm_mode` config key or the `from_orm()` class method. Retaining these deprecated patterns in FastAPI applications causes silent serialization failures or runtime `ValidationError` exceptions when ORM instances are returned from endpoints, with no warning at import or startup time.

## Decision

1. MUST: Set `model_config = ConfigDict(from_attributes=True)` on all Pydantic schemas that serialize ORM model instances.
2. MUST: Replace `Schema.from_orm(instance)` calls with `Schema.model_validate(instance)`.

## Policy Block

- MUST set `model_config = ConfigDict(from_attributes=True)` on all Pydantic schemas that serialize ORM model instances.
- MUST replace `Schema.from_orm(instance)` calls with `Schema.model_validate(instance)`.

In scope:
- FastAPI response schemas that read attributes from SQLAlchemy or other ORM model instances.
- Pydantic v2 model configuration for attribute-based construction.
- Migration from Pydantic v1 `orm_mode` patterns to Pydantic v2 equivalents.

Out of scope:
- Request schemas that parse plain dictionaries — these do not require `from_attributes=True`.
- Non-ORM data sources such as raw SQL query result mappings.
- Pydantic v1 codebases not yet migrated to v2.

Exceptions:
- EXC-001: `model_validate(obj, from_attributes=True)` may be used as a per-call override when modifying the class config is not feasible (e.g., third-party schema).

## Rationale

- Pydantic v2 replaced the `orm_mode` flag with the more descriptive `from_attributes=True`, which accurately names the behavior: constructing a model by reading an object's attributes rather than a dict.
- Migrating `from_orm()` to `model_validate()` aligns with the unified Pydantic v2 validation API and removes a method that no longer exists.

## Consequences

Positive:
- ORM instances are correctly serialized to response schemas without runtime errors or silent empty output.
- Code is forward-compatible with Pydantic v2 and avoids reliance on deprecated compatibility shims.

Negative:
- All existing Pydantic response schemas must be audited and updated during migration, which is a non-trivial sweep across the codebase.
- `from_attributes=True` must only be applied to response/output schemas; applying it to request schemas can mask validation bugs.

## Alternatives

- Remain on Pydantic v1 using compatibility mode (rejected)
  Rejected because: Pydantic v2 does not natively support v1-style `orm_mode`; using the v1 compat layer adds technical debt and forfeits v2 performance and validation improvements.
  When valid: Only when the codebase is explicitly pinned to Pydantic v1 and migration is formally deferred.

## Risks

- Applying `from_attributes=True` to request/input schemas may allow attribute-style construction of unexpected objects, masking validation errors.
  Mitigation: Establish a clear convention that `from_attributes=True` is applied exclusively to response/output schemas and enforce this in code review.