# Deploy FastAPI with Gunicorn Managing Multiple Uvicorn Workers in Production

Status: accepted
Date: 2026-03-31
Deciders: ADR Bank Curation

## Context

- Running uvicorn directly starts a single-process server with no process manager
- A single-process crash kills the entire service with no automatic restart
- There is no graceful reload on deploy when running bare uvicorn
- FastAPI's official deployment documentation explicitly flags bare uvicorn as development-only

## Problem Statement

Bare uvicorn provides no fault tolerance, automatic restart, or graceful deployment reloads, making it unsuitable for production where any unhandled exception terminates the entire service. Gunicorn as a process manager with UvicornWorker provides process supervision, multi-worker concurrency, and zero-downtime restarts without adding significant operational complexity.

## Decision

1. MUST: Run production deployments with Gunicorn using UvicornWorker, not bare uvicorn
2. SHOULD: In containerized environments (Kubernetes, ECS), use a single Uvicorn worker per container and scale via replica count rather than multiple in-process workers
3. SHOULD: Set worker count to (2 × CPU cores) + 1 as the starting baseline for CPU-bound workloads
4. SHOULD: Use --preload to catch import errors at startup before workers fork
5. SHOULD: Set --graceful-timeout 30 to allow in-flight requests to complete before worker restart

## Policy Block

- MUST run production deployments with Gunicorn using UvicornWorker, not bare uvicorn
- SHOULD use a single Uvicorn worker per container in Kubernetes/ECS and scale via replica count
- SHOULD set worker count to (2 × CPU cores) + 1 as the starting baseline
- SHOULD use --preload to surface import errors before workers fork
- SHOULD set --graceful-timeout 30 to allow in-flight requests to complete on restart

In scope:
- FastAPI application production deployment configuration
- Gunicorn worker count tuning for CPU-bound and I/O-bound workloads
- Containerized deployments on Kubernetes, ECS, and similar platforms
- Graceful shutdown and zero-downtime deployment configuration

Out of scope:
- Development and local testing (bare uvicorn with --reload is appropriate)
- ASGI middleware configuration and lifespan event handling
- Load balancer or reverse proxy configuration (nginx, Caddy)
- FastAPI application code structure and routing

Exceptions:
- EXC-001: Serverless deployments (AWS Lambda with Mangum, Google Cloud Run single-instance) bypass Gunicorn entirely—document the deployment target and confirm the runtime provides equivalent process supervision

## Rationale

- Gunicorn provides OS-level process supervision: crashed workers are automatically replaced without service interruption, removing the single-process fragility of bare uvicorn
- The Gunicorn + UvicornWorker combination is the deployment pattern explicitly recommended by FastAPI's documentation, ensuring alignment with upstream-supported configurations and community tooling

## Consequences

Positive:
- Worker crashes are isolated and automatically restarted by Gunicorn, maintaining service availability during transient errors
- Graceful reloads allow deployments to drain in-flight requests before worker replacement, enabling zero-downtime rolling updates

Negative:
- Multiple Gunicorn workers do not share in-process state (caches, connection pools); shared state must be externalized to Redis, a database, or a sidecar service
- Worker count tuning requires empirical load testing; the (2 × CPU) + 1 formula is a starting point, not a universal optimum for I/O-heavy async workloads

## Alternatives

- Running multiple bare uvicorn processes behind a reverse proxy without Gunicorn (rejected)
  Rejected because: Without a process manager, each uvicorn process must be independently supervised by systemd or a container restart policy, adding operational complexity with no benefit over Gunicorn's built-in supervision
  When valid: Only acceptable when deploying to a platform that provides native process supervision per worker instance (e.g., separate containers per worker managed by the orchestrator)

## Risks

- Worker count is set too high for available memory, causing OOM kills that destabilize the service under load
  Mitigation: Monitor worker RSS memory at peak load; enforce a memory limit per worker and treat (2 × CPU) + 1 as a ceiling rather than a floor for memory-constrained environments