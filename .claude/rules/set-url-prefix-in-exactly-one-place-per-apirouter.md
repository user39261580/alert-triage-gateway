---
glob: "**/*.py"
---

<rule_activation adr-id="562f1262-2659-4801-ab31-a420552d1a9b">
<!-- ADR: Set URL Prefix in Exactly One Place per APIRouter -->
</rule_activation>

- Set prefix= either on APIRouter() or on include_router(), never on both for the same router
- Use include_router(prefix='/v1') for API versioning and APIRouter(prefix='/users') for resource grouping
