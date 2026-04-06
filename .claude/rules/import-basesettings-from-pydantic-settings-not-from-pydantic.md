---
glob: "**/*.py"
---

<rule_activation adr-id="20de170e-81a7-4622-a486-8ed79f0fe568">
<!-- ADR: Import BaseSettings from pydantic-settings, Not from pydantic -->
</rule_activation>

- Install pydantic-settings explicitly and import BaseSettings from pydantic_settings, not from pydantic
- Use model_config = SettingsConfigDict(...) instead of a class Config inner class
