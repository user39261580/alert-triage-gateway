---
glob: "**/*.py"
---

<rule_activation adr-id="8173bc55-7176-4b37-bbd0-7dcc4e1df86c">
<!-- ADR: Use TestClient as a Context Manager to Trigger App Lifespan in Tests -->
</rule_activation>

- Use TestClient as a context manager (`with TestClient(app) as client:`) in any test that depends on lifespan-initialized state
- For async test suites, use httpx.AsyncClient with ASGITransport and mark tests with @pytest.mark.anyio
