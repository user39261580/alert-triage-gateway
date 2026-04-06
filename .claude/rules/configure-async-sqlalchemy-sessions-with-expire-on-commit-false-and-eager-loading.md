---
glob: "**/*.py"
---

<rule_activation adr-id="655120c4-658d-4fa8-8e61-59d92b2a4abd">
<!-- ADR: Configure Async SQLAlchemy Sessions with expire_on_commit=False and Eager Loading -->
</rule_activation>

- Create async_sessionmaker with expire_on_commit=False
- Load all required relationships using selectinload or joinedload inside the query — never access relationship attributes after the session closes
