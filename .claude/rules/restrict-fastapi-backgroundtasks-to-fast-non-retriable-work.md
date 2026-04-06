---
glob: "**/*.py"
---

<rule_activation adr-id="1b165179-3082-4cc7-8a81-e1f41650c85b">
<!-- ADR: Restrict FastAPI BackgroundTasks to Fast, Non-Retriable Work -->
</rule_activation>

- Use BackgroundTasks only for fast (sub-100ms), fire-and-forget work where task loss is acceptable
- Use a persistent task queue (Celery, ARQ, or Dramatiq) for any work that must complete reliably or be retried on failure
