---
glob: "**/*.py"
---

<rule_activation adr-id="28771e83-8b6f-4eb9-bef7-d5f914ee197a">
<!-- ADR: Replace @validator and class Config with Pydantic v2 Equivalents -->
</rule_activation>

- Replace @validator with @field_validator in all Pydantic models (Pydantic v2+)
- Replace inner class Config with model_config = ConfigDict(...) at the class body level
- Replace orm_mode=True with ConfigDict(from_attributes=True)
