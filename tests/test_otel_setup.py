"""OTel optional setup tests."""

from __future__ import annotations

from advoi.observability.otel_setup import setup_otel


def test_otel_disabled_by_default():
    assert setup_otel(service_name="test") is False


def test_otel_disabled_without_packages(monkeypatch):
    monkeypatch.setenv("OTEL_ENABLED", "true")
    assert setup_otel(service_name="test") is False