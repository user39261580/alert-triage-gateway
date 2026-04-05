---
glob: "**/*.py"
---

<rule_activation adr-id="394aa621-511f-4ec2-8bf3-012c6f271568">
<!-- ADR: Define Domain Exceptions Without FastAPI Imports and Register Handlers at the App Level -->
</rule_activation>

- Define domain exceptions as plain Python classes in the service layer with no FastAPI imports
- Register exception handlers with @app.exception_handler() in main.py, not inside routers or route functions
- Register on starlette.exceptions.HTTPException to catch route-not-found and method-not-allowed errors
