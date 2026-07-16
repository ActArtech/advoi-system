"""Squad dispatch + multi-agent orchestration."""

from __future__ import annotations

import pytest

from advoi.squads.orchestrate import dispatch_all_squads, run_six_with_platform


@pytest.mark.asyncio
async def test_dispatch_all_squads_mock():
    result = await dispatch_all_squads(confirmed=True)
    assert result["total"] == 5
    assert result["dispatched"] == 5
    assert result["ok"] is True


@pytest.mark.asyncio
async def test_run_six_with_platform_dispatch():
    payload = await run_six_with_platform(
        confirmed=True,
        refresh=True,
        dispatch_squads=True,
        retain_memory=True,
    )
    assert len(payload["results"]) == 6
    assert payload["squads"]["dispatched"] == 5
    assert "spoken_summary" in payload


def test_run_six_api_with_dispatch_squads(client):
    resp = client.post("/api/agents/run-six?refresh=true&dispatch_squads=true")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["results"]) == 6
    assert data["squads"]["dispatched"] == 5


def test_squads_list_api(client):
    resp = client.get("/api/squads")
    assert resp.status_code == 200
    assert resp.json()["total"] == 5


def test_squads_dispatch_all_api(client):
    resp = client.post("/api/squads/dispatch-all")
    assert resp.status_code == 200
    assert resp.json()["dispatched"] == 5


def test_platform_diagnostics_api(client):
    resp = client.get("/api/diagnostics/platform")
    assert resp.status_code == 200
    data = resp.json()
    assert data["multi_agent"]["specialist_count"] == 6
    assert "otel" in data
    assert "otel_ready" in data
    assert "otel_ready" in data["otel"]
    assert data["otel_ready"] == data["otel"]["otel_ready"]
    assert "collector_reachable" in data["otel"]
    assert "squads" in data


@pytest.mark.asyncio
async def test_voice_dispatch_squads():
    from advoi.voice.respond import warm_spoken_reply

    reply = await warm_spoken_reply("dispatch all squads")
    assert reply.action == "dispatch_squads"
    assert "squad" in reply.spoken.lower()
    assert len(reply.agents_used or []) >= 6


def test_latency_includes_run_six(client):
    resp = client.get("/api/diagnostics/latency")
    assert resp.status_code == 200
    timings = resp.json().get("timings_ms") or {}
    assert timings.get("run_six_ms") is not None
    assert timings.get("run_six_frames") == 6
