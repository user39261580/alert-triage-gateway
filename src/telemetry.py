import logging

from opentelemetry import _logs, metrics, trace
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

_LOGGER_HANDLER_MARKER = "_triage_otel_handler"

_trace_provider: TracerProvider | None = None
_meter_provider: MeterProvider | None = None
_log_provider: LoggerProvider | None = None

_request_counter = None
_error_counter = None
_latency_histogram = None
_trust_score_histogram = None


def setup_otel(service_name: str) -> None:
    """Initialize traces, logs, metrics, and DB instrumentation."""
    global _trace_provider, _meter_provider, _log_provider
    global _request_counter, _error_counter, _latency_histogram, _trust_score_histogram

    resource = Resource.create({"service.name": service_name})

    _trace_provider = TracerProvider(resource=resource)
    _trace_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(_trace_provider)

    metric_reader = PeriodicExportingMetricReader(OTLPMetricExporter(), export_interval_millis=5000)
    _meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(_meter_provider)
    meter = metrics.get_meter("alert-triage-gateway")

    _request_counter = meter.create_counter(
        name="triage_requests_total",
        description="Total triage requests processed",
    )
    _error_counter = meter.create_counter(
        name="triage_errors_total",
        description="Total triage requests that ended in error",
    )
    _latency_histogram = meter.create_histogram(
        name="triage_request_latency_ms",
        unit="ms",
        description="Latency of triage requests in milliseconds",
    )
    _trust_score_histogram = meter.create_histogram(
        name="triage_trust_score",
        description="Distribution of computed trust scores",
    )

    _log_provider = LoggerProvider(resource=resource)
    _log_provider.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter()))
    _logs.set_logger_provider(_log_provider)

    root_logger = logging.getLogger()
    if not any(getattr(handler, _LOGGER_HANDLER_MARKER, False) for handler in root_logger.handlers):
        otel_handler = LoggingHandler(level=logging.INFO, logger_provider=_log_provider)
        setattr(otel_handler, _LOGGER_HANDLER_MARKER, True)
        root_logger.addHandler(otel_handler)

    if root_logger.level > logging.INFO:
        root_logger.setLevel(logging.INFO)

    psycopg2_instrumentor = Psycopg2Instrumentor()
    if not psycopg2_instrumentor.is_instrumented_by_opentelemetry:
        psycopg2_instrumentor.instrument()


def record_triage_metrics(
    *,
    model: str,
    status: str,
    latency_ms: float,
    trust_score: float | None = None,
) -> None:
    """Record request-level metrics for triage endpoint behavior."""
    if _request_counter is None:
        return

    attrs = {
        "endpoint": "/api/v1/triage-alert",
        "model": model,
        "status": status,
    }

    _request_counter.add(1, attrs)

    if _latency_histogram is not None:
        _latency_histogram.record(latency_ms, attrs)

    if status == "error" and _error_counter is not None:
        _error_counter.add(1, attrs)

    if trust_score is not None and _trust_score_histogram is not None:
        _trust_score_histogram.record(trust_score, {"model": model})


def shutdown_otel() -> None:
    """Flush and stop telemetry providers on application shutdown."""
    if _meter_provider is not None:
        _meter_provider.shutdown()
    if _trace_provider is not None:
        _trace_provider.shutdown()
    if _log_provider is not None:
        _log_provider.shutdown()
