# Import BaseSettings from pydantic-settings, Not from pydantic

Status: accepted
Date: 2026-03-31
Deciders: ADR Bank Curation

## Context

- In FastAPI 0.100+ (Pydantic v2), BaseSettings was removed from the core pydantic package and moved to the separate pydantic-settings package.
- Code importing BaseSettings from pydantic raises ImportError at runtime.
- The failure can be masked during development if .env-based initialization hides the broken import path (e.g., when environment variables are set directly and the settings class is never actually instantiated in dev).
- The inner class Config pattern was also replaced with model_config = SettingsConfigDict(...) in Pydantic v2.

## Problem Statement

Importing BaseSettings from pydantic instead of pydantic_settings in FastAPI 0.100+ / Pydantic v2 raises a runtime ImportError that may be masked during development, causing production failures when the settings class is first instantiated in a deployed environment.

## Decision

1. MUST: Install pydantic-settings explicitly as a dependency.
2. MUST: Import BaseSettings from pydantic_settings, not from pydantic.
3. MUST: Use model_config = SettingsConfigDict(...) instead of a class Config inner class.
4. SHOULD: Replace `from pydantic import BaseSettings` with `from pydantic_settings import BaseSettings, SettingsConfigDict` in all settings modules.

## Policy Block

- MUST install pydantic-settings explicitly as a project dependency.
- MUST import BaseSettings from pydantic_settings, not from pydantic.
- MUST use model_config = SettingsConfigDict(...) instead of inner class Config.
- SHOULD import SettingsConfigDict alongside BaseSettings from pydantic_settings.

In scope:
- FastAPI 0.100+ and Pydantic v2 settings configuration
- All Python modules that define application settings classes inheriting from BaseSettings
- Migration from Pydantic v1 BaseSettings to pydantic-settings package

Out of scope:
- Pydantic BaseModel usage (unaffected by this change)
- Pydantic v1 projects not upgrading to v2
- Non-BaseSettings configuration approaches (e.g., plain dataclasses, environ, dynaconf)

Exceptions:
- EXC-001: Projects pinned to Pydantic v1 (pydantic<2.0) should continue importing from pydantic until the v2 migration is undertaken.

## Rationale

- Pydantic v2 explicitly removed BaseSettings from the core package to reduce the dependency footprint; the separate pydantic-settings package is the only supported location.
- Using model_config = SettingsConfigDict(...) aligns with Pydantic v2's configuration pattern and enables proper type checking and IDE support.
- Catching this import error early (via correct imports) prevents masked failures that only surface in production.

## Consequences

Positive:
- Settings classes work correctly with Pydantic v2 and FastAPI 0.100+ without runtime import errors.
- Configuration follows the Pydantic v2 idiomatic pattern, improving compatibility with tooling, type checkers, and IDE autocompletion.
- Explicit dependency declaration makes the pydantic-settings requirement visible in requirements files.

Negative:
- Adds an additional package dependency (pydantic-settings) that must be tracked and version-managed.
- Existing codebases require a migration step to update all BaseSettings imports and replace class Config with model_config.

## Alternatives

- Pin to Pydantic v1 and continue importing BaseSettings from pydantic (rejected)
  Rejected because: Pydantic v1 is in maintenance mode and will not receive new features or performance improvements. FastAPI 0.100+ is designed for Pydantic v2 and future FastAPI versions may drop v1 support entirely.
  When valid: In legacy projects with extensive Pydantic v1 usage where a full migration is not yet feasible.

## Risks

- Developers copy code snippets from pre-v2 tutorials or documentation that still show `from pydantic import BaseSettings`, reintroducing the broken import.
  Mitigation: Add a linting rule (e.g., via ruff or a custom flake8 plugin) that flags `from pydantic import BaseSettings` and suggests the pydantic_settings import instead.