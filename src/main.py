import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from langfuse import get_client
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def _setup_otel() -> None:
    """Initialize OTel with OTLP export and psycopg2 instrumentation."""
    service_name = os.getenv("OTEL_SERVICE_NAME", "alert-triage-gateway")
    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)
    Psycopg2Instrumentor().instrument()


_setup_otel()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    get_client().flush()


app = FastAPI(title="Alert Triage Gateway", version="0.1.0", lifespan=lifespan)
FastAPIInstrumentor.instrument_app(app)

from src.routers.triage import router  # noqa: E402

app.include_router(router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
