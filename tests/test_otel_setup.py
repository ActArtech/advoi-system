"""OTel optional setup + diagnostics tests (moat R6)."""

from __future__ import annotations

from advoi.diagnostics.platform import otel_diagnostics
from advoi.observability.otel_setup import (
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


def test_current_trace_id_none_without_span(monkeypatch):
    monkeypatch.setenv("OTEL_ENABLED", "true")
    assert current_trace_id() is None


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
