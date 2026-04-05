---
glob: "**/*.py"
---

<rule_activation adr-id="a2cdbfee-c72b-4ef2-bdef-1f25ad93c3d9">
<!-- ADR: Replace orm_mode = True with ConfigDict(from_attributes=True) for ORM Response Schemas -->
</rule_activation>

- Set model_config = ConfigDict(from_attributes=True) on all Pydantic schemas that serialize ORM model instances
- Replace Schema.from_orm(instance) calls with Schema.model_validate(instance)
