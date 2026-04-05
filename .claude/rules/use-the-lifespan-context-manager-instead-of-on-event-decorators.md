---
glob: "**/*.py"
---

<rule_activation adr-id="2061e8dd-5e97-47ed-9c77-d4d5f403bc3d">
<!-- ADR: Use the Lifespan Context Manager Instead of on_event Decorators -->
</rule_activation>

- Define all startup and shutdown logic in an @asynccontextmanager function passed as lifespan= to FastAPI()
- Never use @app.on_event('startup') or @app.on_event('shutdown') in FastAPI 0.93+
