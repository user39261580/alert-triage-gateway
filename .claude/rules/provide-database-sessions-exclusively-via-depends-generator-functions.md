---
glob: "**/*.py"
---

<rule_activation adr-id="8ec77825-2b36-44b8-8f18-96ba28a43bf4">
<!-- ADR: Provide Database Sessions Exclusively via Depends() Generator Functions -->
</rule_activation>

- Provide all database sessions via a Depends() generator function — never instantiate Session or AsyncSession directly inside a route handler body or as a module-level global
