import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from langfuse import get_client
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.telemetry import record_healthcheck, setup_otel, shutdown_otel


def _setup_observability() -> None:
    """Initialize app observability for traces, logs, and metrics."""
    service_name = os.getenv("OTEL_SERVICE_NAME", "alert-triage-gateway")
    setup_otel(service_name)


_setup_observability()
logger = logging.getLogger("alert-triage-gateway.errors")


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    get_client().flush()
    shutdown_otel()


app = FastAPI(title="Alert Triage Gateway", version="0.1.0", lifespan=lifespan)
FastAPIInstrumentor.instrument_app(app)


@app.exception_handler(StarletteHTTPException)
async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Return a consistent JSON shape for HTTP framework and route errors."""
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": "http_error",
                "message": detail,
                "path": request.url.path,
                "status_code": exc.status_code,
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Return validation errors in the same JSON envelope as other API errors."""
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "type": "validation_error",
                "message": "Request validation failed",
                "path": request.url.path,
                "status_code": 422,
                "details": exc.errors(),
            }
        },
    )


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    """Prevent HTML 500 responses by returning a stable JSON error contract."""
    logger.exception("unhandled_exception", extra={"path": request.url.path})
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "type": "internal_server_error",
                "message": "Internal server error",
                "path": request.url.path,
                "status_code": 500,
            }
        },
    )

from src.routers.triage import router  # noqa: E402

app.include_router(router)


@app.get("/health")
async def health() -> dict[str, str]:
    record_healthcheck()
    return {"status": "ok"}
