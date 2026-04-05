---
glob: "**/*.py"
---

<rule_activation adr-id="bb1e4dfa-07d6-46b8-a26a-478a190ff732">
<!-- ADR: Cache Settings with @lru_cache and Expose via Depends for Testability -->
</rule_activation>

- Wrap the Settings() constructor in a @lru_cache function and expose it as a FastAPI dependency
- Never instantiate Settings() at module level in business logic or router modules
