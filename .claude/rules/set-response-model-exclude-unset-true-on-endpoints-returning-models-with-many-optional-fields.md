---
glob: "**/*.py"
---

<rule_activation adr-id="42bea9dd-fd4e-46ce-b670-e67c4a0a1108">
<!-- ADR: Set response_model_exclude_unset=True on Endpoints Returning Models with Many Optional Fields -->
</rule_activation>

- Set response_model_exclude_unset=True on endpoints whose response_model contains multiple Optional fields
- Never use ORM model classes directly as response_model — define dedicated Pydantic response schemas
