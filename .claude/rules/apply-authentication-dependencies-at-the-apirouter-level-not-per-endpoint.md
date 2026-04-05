---
glob: "**/*.py"
---

<rule_activation adr-id="fbd0b83d-c17b-496b-a5e6-fbf72085a4aa">
<!-- ADR: Apply Authentication Dependencies at the APIRouter Level, Not Per-Endpoint -->
</rule_activation>

- Apply authentication dependencies via dependencies=[Depends(...)] on the APIRouter constructor, not on individual route function signatures
- Use separate APIRouter instances for public and authenticated route groups
