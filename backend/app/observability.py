import json
import logging
import re
import time
from contextvars import ContextVar
from datetime import datetime, timezone
from uuid import uuid4

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from prometheus_client import Counter, Histogram, make_asgi_app


REQUEST_ID_HEADER = b"x-request-id"
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
REQUEST_ID: ContextVar[str] = ContextVar("lab_agent_request_id", default="-")
SAFE_LOG_FIELDS = (
    "blocked_reason",
    "error_type",
    "fallback",
    "intent",
    "latency_ms",
    "phase",
    "plan_id",
    "plan_mode",
    "plan_status",
    "plan_step",
    "route_source",
    "router_version",
    "speech_act",
    "status_code",
    "tool_name",
    "user_id",
)
KNOWN_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"}

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
AGENT_TOOL_CALLS = Counter(
    "lab_agent_tool_calls_total",
    "Tool calls performed by the agent",
    ["tool", "outcome"],
)
AGENT_PLAN_EVENTS = Counter(
    "lab_agent_plan_events_total",
    "Plan execution lifecycle events",
    ["mode", "step", "status"],
)


class JsonFormatter(logging.Formatter):
    # 将输入记录转换为结构化输出。
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": REQUEST_ID.get(),
        }
        for field in SAFE_LOG_FIELDS:
            value = getattr(record, field, None)
            if isinstance(value, (str, int, float, bool)):
                payload[field] = value[:160] if isinstance(value, str) else value

        try:
            from opentelemetry import trace

            span_context = trace.get_current_span().get_span_context()
            if span_context.is_valid:
                payload["trace_id"] = f"{span_context.trace_id:032x}"
                payload["span_id"] = f"{span_context.span_id:016x}"
        except ImportError:
            pass

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


class RequestContextFilter(logging.Filter):
    # 补充日志上下文并决定当前记录是否继续处理。
    def filter(self, record: logging.LogRecord) -> bool:
        request_id = REQUEST_ID.get()
        if request_id != "-":
            record.request_id = request_id
        return True


class RequestMetricsMiddleware:
    """ASGI middleware that preserves streaming and bounds metric labels."""

    # 初始化对象状态和依赖。
    def __init__(self, app):
        self.app = app

    # 处理对象调用请求并返回结果。
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        candidate = headers.get(REQUEST_ID_HEADER, b"").decode("latin-1")
        request_id = candidate if REQUEST_ID_PATTERN.fullmatch(candidate) else uuid4().hex
        scope.setdefault("state", {})["request_id"] = request_id
        token = REQUEST_ID.set(request_id)
        started = time.perf_counter()
        status = 500

        # 发送响应并确保请求 ID 被正确返回。
        async def send_with_request_id(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                response_headers = list(message.get("headers", []))
                if not any(key.lower() == REQUEST_ID_HEADER for key, _ in response_headers):
                    response_headers.append((REQUEST_ID_HEADER, request_id.encode("ascii")))
                message = {**message, "headers": response_headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            route = scope.get("route")
            path = getattr(route, "path", None) or "__unmatched__"
            method = scope.get("method", "OTHER").upper()
            if method not in KNOWN_METHODS:
                method = "OTHER"
            REQUEST_COUNT.labels(method, path, str(status)).inc()
            REQUEST_LATENCY.labels(method, path).observe(time.perf_counter() - started)
            REQUEST_ID.reset(token)


# 配置logging相关数据或业务逻辑。
def configure_logging() -> None:
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    configured = False
    for handler in root.handlers:
        if not any(isinstance(item, RequestContextFilter) for item in handler.filters):
            handler.addFilter(RequestContextFilter())
        if isinstance(handler, logging.StreamHandler):
            handler.setFormatter(JsonFormatter())
            configured = True
    if not configured:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        handler.addFilter(RequestContextFilter())
        root.addHandler(handler)


# 配置tracing相关数据或业务逻辑。
def configure_tracing(app, service_name: str, endpoint: str | None) -> None:
    if not endpoint:
        return
    try:
        from opentelemetry import trace
        from opentelemetry._logs import set_logger_provider
        from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
        from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create({"service.name": service_name})
        tracer_provider = TracerProvider(resource=resource)
        tracer_provider.add_span_processor(
            BatchSpanProcessor(
                OTLPSpanExporter(endpoint=f"{endpoint.rstrip('/')}/v1/traces")
            )
        )
        trace.set_tracer_provider(tracer_provider)

        logger_provider = LoggerProvider(resource=resource)
        logger_provider.add_log_record_processor(
            BatchLogRecordProcessor(
                OTLPLogExporter(endpoint=f"{endpoint.rstrip('/')}/v1/logs")
            )
        )
        set_logger_provider(logger_provider)
        otel_handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
        otel_handler.addFilter(RequestContextFilter())
        logging.getLogger().addHandler(otel_handler)

        FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)
        app.add_event_handler("shutdown", tracer_provider.shutdown)
        app.add_event_handler("shutdown", logger_provider.shutdown)
        logging.getLogger(__name__).info(
            "OpenTelemetry tracing and log export enabled",
            extra={"service_name": service_name},
        )
    except ImportError:
        logging.getLogger(__name__).warning(
            "OpenTelemetry packages are not installed; export is disabled"
        )


# 获取tracer相关数据或业务逻辑。
def get_tracer(name: str):
    return trace.get_tracer(name)


# 负责 mark span error 相关逻辑，并返回处理结果。
def mark_span_error(span, error: Exception) -> None:
    span.set_attribute("error.type", type(error).__name__)
    span.set_status(Status(StatusCode.ERROR))


def record_plan_event(
    *,
    plan_id: str,
    plan_mode: str,
    plan_step: str,
    plan_status: str,
    blocked_reason: str | None = None,
    selection_required: bool = False,
    confirmation_required: bool = False,
) -> None:
    """Record a bounded, non-sensitive plan lifecycle event."""
    AGENT_PLAN_EVENTS.labels(plan_mode, plan_step, plan_status).inc()
    current_span = trace.get_current_span()
    if current_span.get_span_context().is_valid:
        current_span.set_attribute("agent.plan.id", plan_id)
        current_span.set_attribute("agent.plan.mode", plan_mode)
        current_span.set_attribute("agent.plan.step", plan_step)
        current_span.set_attribute("agent.plan.status", plan_status)
        current_span.set_attribute("agent.plan.selection_required", selection_required)
        current_span.set_attribute("agent.plan.confirmation_required", confirmation_required)
        if blocked_reason:
            current_span.set_attribute("agent.plan.blocked_reason", blocked_reason)
    logging.getLogger("agent.plan").info(
        "agent plan event",
        extra={
            "plan_id": plan_id,
            "plan_mode": plan_mode,
            "plan_step": plan_step,
            "plan_status": plan_status,
            "blocked_reason": blocked_reason,
        },
    )


# 调用tool相关数据或业务逻辑。
def invoke_tool(tool, arguments):
    with get_tracer("lab-agent.tools").start_as_current_span(
        "agent.tool.invoke",
        record_exception=False,
        set_status_on_exception=False,
    ) as span:
        span.set_attribute("agent.tool.name", tool.name)
        try:
            result = tool.invoke(arguments)
            try:
                payload = json.loads(result) if isinstance(result, str) else result
                succeeded = bool(payload.get("ok")) if isinstance(payload, dict) else True
            except (TypeError, json.JSONDecodeError):
                succeeded = False
            outcome = "success" if succeeded else "failure"
            span.set_attribute("agent.tool.outcome", outcome)
            if not succeeded:
                span.set_status(Status(StatusCode.ERROR, "tool returned failure"))
            AGENT_TOOL_CALLS.labels(tool.name, outcome).inc()
            return result
        except Exception as exc:
            mark_span_error(span, exc)
            AGENT_TOOL_CALLS.labels(tool.name, "error").inc()
            raise


# 安装observability相关数据或业务逻辑。
def install_observability(app, service_name: str, otlp_endpoint: str | None) -> None:
    configure_logging()
    app.add_middleware(RequestMetricsMiddleware)
    app.mount("/metrics", make_asgi_app())
    configure_tracing(app, service_name, otlp_endpoint)
