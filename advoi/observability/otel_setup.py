"""Optional OpenTelemetry setup — no-op when OTEL_ENABLED is false or SDK missing."""

from __future__ import annotations

import logging
import os
from typing import Any
from urllib.parse import urlparse

_LOGGER = logging.getLogger(__name__)


def otel_enabled() -> bool:
    return os.getenv("OTEL_ENABLED", "false").lower() in {"1", "true", "yes"}


def current_trace_id() -> str | None:
    """Best-effort OTel / request correlation id; None when unavailable."""
    if not otel_enabled():
        return None
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        ctx = span.get_span_context() if span is not None else None
        if ctx is None or not getattr(ctx, "is_valid", False):
            return None
        return format(ctx.trace_id, "032x")
    except Exception:
        return None


def parse_otlp_endpoint(endpoint: str | None = None) -> tuple[str, int]:
    """Return (host, port) for OTLP endpoint URL or host:port string."""
    raw = (endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://127.0.0.1:4317")).strip()
    if "://" not in raw:
        raw = f"http://{raw}"
    parsed = urlparse(raw)
    host = parsed.hostname or "127.0.0.1"
    if parsed.port is not None:
        port = parsed.port
    elif parsed.scheme == "https":
        port = 443
    else:
        # gRPC OTLP default
        port = 4317
    return host, port


def probe_collector_reachable(
    endpoint: str | None = None,
    *,
    timeout_s: float = 0.5,
) -> bool:
    """TCP reachability check against the OTLP collector endpoint."""
    import socket

    host, port = parse_otlp_endpoint(endpoint)
    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            return True
    except OSError:
        return False


def setup_otel(app: Any | None = None, *, service_name: str = "advoi") -> bool:
    """Instrument FastAPI when OTEL_ENABLED=true and opentelemetry packages are installed."""
    if not otel_enabled():
        return False
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        _LOGGER.info(
            "OTEL_ENABLED but opentelemetry packages missing — "
            "install optional [observability] deps"
        )
        return False

    # gRPC OTLP exporter — use port 4317 (not HTTP 4318)
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://127.0.0.1:4317")
    resource = Resource.create(
        {
            "service.name": os.getenv("OTEL_SERVICE_NAME", service_name),
            "service.version": os.getenv("ADVOI_VERSION", "0.1.0"),
        }
    )
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=True))
    )
    trace.set_tracer_provider(provider)

    if app is not None:
        FastAPIInstrumentor.instrument_app(app)

    _LOGGER.info("OpenTelemetry enabled for %s -> %s", service_name, endpoint)
    return True
