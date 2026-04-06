---
glob: "**/*.py"
---

<rule_activation adr-id="05c008e4-eaf3-4dbe-b3b0-ea84bbbc38dc">
<!-- ADR: Deploy FastAPI with Gunicorn Managing Multiple Uvicorn Workers in Production -->
</rule_activation>

- Run production deployments with Gunicorn using UvicornWorker, not bare uvicorn
- In containerized environments (Kubernetes, ECS), use a single Uvicorn worker per container and scale via replica count rather than multiple in-process workers
