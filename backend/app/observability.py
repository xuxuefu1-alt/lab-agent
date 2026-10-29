import json
import logging
import time
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_client import Counter, Histogram, make_asgi_app


REQUEST_COUNT = Counter(
    "lab_agent_http_requests_total",
    "Total HTTP requests handled by the API",
    ["method", "path", "status"],
)
REQUEST_LATENCY = Histogram(
    "lab_agent_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        started = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            path = request.url.path
            REQUEST_COUNT.labels(request.method, path, str(status)).inc()
            REQUEST_LATENCY.labels(request.method, path).observe(
                time.perf_counter() - started
            )


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)


def configure_tracing(app, service_name: str, endpoint: str | None) -> None:
    if not endpoint:
        return
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        provider = TracerProvider(
            resource=Resource.create({"service.name": service_name})
        )
        exporter = OTLPSpanExporter(
            endpoint=f"{endpoint.rstrip('/')}/v1/traces"
        )
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(app)
        logging.getLogger(__name__).info(
            "OpenTelemetry tracing enabled",
            extra={"endpoint": endpoint, "service_name": service_name},
        )
    except ImportError:
        logging.getLogger(__name__).warning(
            "OpenTelemetry packages are not installed; tracing is disabled"
        )


def install_observability(app, service_name: str, otlp_endpoint: str | None) -> None:
    configure_logging()
    app.add_middleware(MetricsMiddleware)
    app.mount("/metrics", make_asgi_app())
    configure_tracing(app, service_name, otlp_endpoint)
