# Replace @validator and class Config with Pydantic v2 Equivalents

Status: accepted
Date: 2026-03-31
Deciders: ADR Bank Curation

## Context

- `@validator` and `class Config` are still importable in Pydantic v2 but emit only deprecation warnings — they do not cause runtime failures.
- Mixed v1/v2 codebases silently accumulate technical debt as deprecated patterns persist alongside modern equivalents.
- Deprecated v1 patterns may produce subtly incorrect validation behavior when combined with v2 features such as `model_validator` or `ConfigDict`.
- Pydantic v2 provides direct replacements: `@field_validator` for `@validator`, and `model_config = ConfigDict(...)` for `class Config`.

## Problem Statement

Without migrating away from deprecated Pydantic v1 patterns, codebases accumulate silent technical debt and risk subtly incorrect validation behavior when v1 and v2 patterns coexist in the same model hierarchy.

## Decision

1. MUST: Replace `@validator` with `@field_validator` in all Pydantic models (Pydantic v2+).
2. MUST: Replace inner `class Config` with `model_config = ConfigDict(...)` at the class body level.
3. MUST: Replace `orm_mode=True` with `ConfigDict(from_attributes=True)`.
4. SHOULD: Remove `each_item=True` from any validator and use `Annotated` item validators in v2 instead.
5. SHOULD: Use `bump-pydantic` CLI tool to automate bulk conversions.

## Policy Block

- MUST replace `@validator` with `@field_validator` in all Pydantic models.
- MUST replace inner `class Config` with `model_config = ConfigDict(...)` at the class body level.
- MUST replace `orm_mode=True` with `ConfigDict(from_attributes=True)`.
- SHOULD remove `each_item=True` from any validator and use `Annotated` item validators in v2 instead.
- SHOULD use `bump-pydantic` CLI tool (`pip install bump-pydantic && bump-pydantic .`) to automate most conversions.
- SHOULD use `mode='before'` explicitly when converting `@validator` to `@field_validator` to preserve pre-validation behavior.

In scope:
- All Python files containing Pydantic `BaseModel` subclasses.
- Migration of `@validator` → `@field_validator` decorator usage.
- Migration of `class Config` → `model_config = ConfigDict(...)` configuration pattern.
- Migration of `orm_mode` → `from_attributes` configuration key.
- Removal of `each_item=True` in favor of `Annotated` item validators.

Out of scope:
- Migration of `@root_validator` to `@model_validator` (covered by a separate ADR).
- Migration of `.dict()` / `.json()` to `.model_dump()` / `.model_dump_json()` (separate concern).
- Pydantic v1-only codebases that have not yet upgraded to v2.

Exceptions:
- EXC-001: Third-party library models that inherit from Pydantic v1 base classes and cannot be modified may retain v1 patterns until the library is updated.

## Rationale

- Pydantic v2 deprecation warnings will eventually become errors in Pydantic v3, so migrating now avoids a forced bulk migration later.
- Consistent use of v2 patterns across the codebase eliminates ambiguity about which API surface is canonical.
- `@field_validator` provides clearer semantics with explicit `mode='before'` / `mode='after'` instead of v1's implicit behavior.

## Consequences

Positive:
- Eliminates deprecation warnings from test and CI output, making real warnings visible.
- Ensures validation behavior is explicit and predictable under the v2 engine.
- Reduces risk of subtle bugs when v1 and v2 validators interact in inherited models.

Negative:
- Requires a one-time migration effort across all existing models, which may be significant in large codebases.
- `@field_validator` has slightly different argument ordering and semantics compared to `@validator`, requiring careful review during conversion.

## Alternatives

- Leave v1 patterns in place and rely on Pydantic's backward compatibility layer. (rejected)
  Rejected because: Deprecated patterns accumulate technical debt and risk breakage in Pydantic v3. Mixed codebases confuse contributors about which API to use.
  When valid: Acceptable only as a temporary state during an incremental migration, not as a permanent strategy.

## Risks

- Automated migration tools like `bump-pydantic` may miss edge cases such as dynamic validator registration or complex inheritance hierarchies.
  Mitigation: Run the full test suite after automated conversion and manually review any models with custom `__init_subclass__` or metaclass logic.