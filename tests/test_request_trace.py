"""Request trace middleware tests."""

from __future__ import annotations


def test_health_includes_trace_headers(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.headers.get("x-request-id")
    assert resp.headers.get("x-response-time-ms")