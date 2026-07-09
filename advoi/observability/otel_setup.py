"""Optional OpenTelemetry setup — no-op when OTEL_ENABLED is false or SDK missing."""

from __future__ import annotations

import logging
import os
from typing import Any

_LOGGER = logging.getLogger(__name__)


def _otel_enabled() -> bool:
    return os.getenv("OTEL_ENABLED", "false").lower() in {"1", "true", "yes"}


def setup_otel(app: Any | None = None, *, service_name: str = "advoi") -> bool:
    """Instrument FastAPI when OTEL_ENABLED=true and opentelemetry packages are installed."""
    if not _otel_enabled():
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
            "OTEL_ENABLED but opentelemetry packages missing — install optional [observability] deps"
        )
        return False

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://127.0.0.1:4317")
    resource = Resource.create(
        {
            "service.name": os.getenv("OTEL_SERVICE_NAME", service_name),
            "service.version": os.getenv("ADVOI_VERSION", "0.1.0"),
        }
    )
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=True)))
    trace.set_tracer_provider(provider)

    if app is not None:
        FastAPIInstrumentor.instrument_app(app)

    _LOGGER.info("OpenTelemetry enabled for %s -> %s", service_name, endpoint)
    return True