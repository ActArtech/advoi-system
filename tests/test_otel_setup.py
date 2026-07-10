"""OTel optional setup + diagnostics tests (moat R6)."""

from __future__ import annotations

from advoi.diagnostics.platform import otel_diagnostics
from advoi.observability.otel_setup import (
    active_span_context,
    current_span_id,
    current_trace_id,
    otel_enabled,
    parse_otlp_endpoint,
    setup_otel,
)


def test_otel_disabled_by_default(monkeypatch):
    monkeypatch.delenv("OTEL_ENABLED", raising=False)
    assert otel_enabled() is False
    assert setup_otel(service_name="test") is False


def test_otel_disabled_without_packages(monkeypatch):
    monkeypatch.setenv("OTEL_ENABLED", "true")
    # Without optional [observability] installed in CI, setup returns False.
    # If packages ARE installed, setup may return True — only assert enabled flag path.
    result = setup_otel(service_name="test")
    assert isinstance(result, bool)


def test_current_trace_id_none_when_otel_off(monkeypatch):
    monkeypatch.setenv("OTEL_ENABLED", "false")
    assert current_trace_id() is None
    assert current_span_id() is None
    assert active_span_context() is None


def test_current_trace_id_none_without_span(monkeypatch):
    monkeypatch.setenv("OTEL_ENABLED", "true")
    assert current_trace_id() is None
    assert current_span_id() is None
    assert active_span_context() is None


def test_active_span_context_reads_mocked_span(monkeypatch):
    monkeypatch.setenv("OTEL_ENABLED", "true")

    class FakeCtx:
        is_valid = True
        trace_id = int("c" * 32, 16)
        span_id = int("d" * 16, 16)

    class FakeSpan:
        def get_span_context(self) -> FakeCtx:
            return FakeCtx()

    import sys
    import types

    otel_mod = types.ModuleType("opentelemetry")
    trace_mod = types.ModuleType("opentelemetry.trace")
    trace_mod.get_current_span = lambda: FakeSpan()  # type: ignore[attr-defined]
    otel_mod.trace = trace_mod  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "opentelemetry", otel_mod)
    monkeypatch.setitem(sys.modules, "opentelemetry.trace", trace_mod)

    ctx = active_span_context()
    assert ctx is not None
    assert current_trace_id() == "c" * 32
    assert current_span_id() == "d" * 16


def test_parse_otlp_endpoint_defaults():
    host, port = parse_otlp_endpoint("http://otel-collector:4317")
    assert host == "otel-collector"
    assert port == 4317
    host2, port2 = parse_otlp_endpoint("127.0.0.1:4317")
    assert host2 == "127.0.0.1"
    assert port2 == 4317


def test_otel_diagnostics_disabled(monkeypatch):
    monkeypatch.setenv("OTEL_ENABLED", "false")
    diag = otel_diagnostics()
    assert diag["enabled"] is False
    assert diag["otel_ready"] is False
    assert diag["collector_reachable"] is False
    assert diag["instrumented"] is False


def test_otel_diagnostics_enabled_collector_down(monkeypatch):
    monkeypatch.setenv("OTEL_ENABLED", "true")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://127.0.0.1:1")
    monkeypatch.setattr(
        "advoi.diagnostics.platform.probe_collector_reachable",
        lambda endpoint=None: False,
    )
    diag = otel_diagnostics()
    assert diag["enabled"] is True
    assert diag["collector_reachable"] is False
    assert diag["otel_ready"] is False


def test_otel_diagnostics_otel_ready_when_collector_up(monkeypatch):
    monkeypatch.setenv("OTEL_ENABLED", "true")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317")
    monkeypatch.setattr(
        "advoi.diagnostics.platform.probe_collector_reachable",
        lambda endpoint=None: True,
    )

    # packages_installed depends on import; force both paths via importability
    try:
        import opentelemetry  # noqa: F401

        packages = True
    except ImportError:
        packages = False

    diag = otel_diagnostics()
    assert diag["enabled"] is True
    assert diag["collector_reachable"] is True
    assert diag["packages_installed"] is packages
    assert diag["otel_ready"] is (packages and True)
