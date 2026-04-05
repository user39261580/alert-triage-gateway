---
glob: "**/*.py"
---

<rule_activation adr-id="08ca262f-0e3b-497a-97ca-35b412797de9">
<!-- ADR: Use model_dump(exclude_unset=True) When Merging PATCH Payloads into Stored Records -->
</rule_activation>

- Call patch_body.model_dump(exclude_unset=True) when merging a PATCH payload into a stored record
- Define a separate request schema for PATCH endpoints with all fields typed as Optional[T] with None defaults — never reuse the POST create schema
