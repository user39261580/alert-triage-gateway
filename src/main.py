import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from langfuse import get_client
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from src.telemetry import setup_otel, shutdown_otel


def _setup_observability() -> None:
    """Initialize app observability for traces, logs, and metrics."""
    service_name = os.getenv("OTEL_SERVICE_NAME", "alert-triage-gateway")
    setup_otel(service_name)


_setup_observability()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    get_client().flush()
    shutdown_otel()


app = FastAPI(title="Alert Triage Gateway", version="0.1.0", lifespan=lifespan)
FastAPIInstrumentor.instrument_app(app)

from src.routers.triage import router  # noqa: E402

app.include_router(router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
