"""Run-all agents API tests."""

from __future__ import annotations


def test_run_all_agents_parallel(client):
    resp = client.post("/api/agents/run-all?refresh=true&confirmed=true")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["results"]) == 6
    frame_ids = {row["frame_id"] for row in data["results"]}
    assert frame_ids == {
        "fleet_status",
        "open_briefs",
        "queue_deep_review",
        "systems_pulse",
        "memory_health",
        "guardian_status",
    }
    assert "systems-pulse" in data["agents_used"]


def test_run_six_alias(client):
    resp = client.post("/api/agents/run-six?refresh=true&confirmed=true")
    assert resp.status_code == 200
    assert len(resp.json()["results"]) == 6


def test_memory_diagnostics(client):
    resp = client.get("/api/diagnostics/memory")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert "operational_store_enabled" in data