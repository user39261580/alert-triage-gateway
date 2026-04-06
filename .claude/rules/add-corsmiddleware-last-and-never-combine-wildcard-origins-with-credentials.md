---
glob: "**/*.py"
---

<rule_activation adr-id="9e55acce-0716-49d8-a897-52f8c3629da8">
<!-- ADR: Add CORSMiddleware Last and Never Combine Wildcard Origins with Credentials -->
</rule_activation>

- Call app.add_middleware(CORSMiddleware, ...) after all other add_middleware calls
- Never combine allow_origins=['*'] with allow_credentials=True — enumerate allowed origins explicitly when credentials are required
