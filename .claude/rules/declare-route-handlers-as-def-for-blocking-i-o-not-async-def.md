---
glob: "**/*.py"
---

<rule_activation adr-id="a70b989e-fe25-47d2-9768-876a0aab3024">
<!-- ADR: Declare Route Handlers as def for Blocking I/O, Not async def -->
</rule_activation>

- Use def (not async def) for route handlers that call any synchronous blocking I/O library
- Use async def only when all I/O inside the handler uses await
- Never call time.sleep() inside async def — use await asyncio.sleep() instead
