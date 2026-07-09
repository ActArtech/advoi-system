"""Agent daemon stop/restart control."""

import pytest

from advoi.cache.redis_client import redis_available
from advoi.routing.agent_control import (
    agents_paused,
    restart_agent_daemons,
    set_agents_paused,
    stop_agent_daemons,
)
from advoi.voice.capabilities import classify_operator_intent
from advoi.voice.respond import warm_spoken_reply


@pytest.mark.asyncio
async def test_stop_and_restart_agents(monkeypatch):
    monkeypatch.setenv("ADVOI_CONFIRMATION_REQUIRED", "false")
    stop = await stop_agent_daemons(docker=False)
    assert stop["ok"] is True
    assert stop["paused"] is True
    assert agents_paused() is True

    restart = await restart_agent_daemons(docker=False, prewarm=True)
    assert restart["ok"] is True
    assert restart["paused"] is False
    assert agents_paused() is False
    assert restart["prewarmed"] >= 0

    set_agents_paused(False)


@pytest.mark.asyncio
async def test_stop_agents_confirm_gate():
    reply = await warm_spoken_reply("stop agents")
    assert reply.action == "confirmation_required"
    assert "confirm" in reply.spoken.lower()


@pytest.mark.asyncio
async def test_stop_agents_with_confirm(monkeypatch):
    monkeypatch.setenv("ADVOI_CONFIRMATION_REQUIRED", "true")
    reply = await warm_spoken_reply("stop agents confirm")
    assert reply.action == "stop_agents"
    assert "paused" in reply.spoken.lower()
    set_agents_paused(False)


@pytest.mark.asyncio
async def test_restart_agents_voice():
    reply = await warm_spoken_reply("restart agents")
    assert reply.action == "restart_agents"
    assert "restart" in reply.spoken.lower()


@pytest.mark.parametrize(
    "transcript,expected",
    [
        ("stop agents", "stop_agents"),
        ("pause agent daemons", "stop_agents"),
        ("restart agents", "restart_agents"),
        ("start agents again", "restart_agents"),
    ],
)
def test_classify_stop_restart(transcript, expected):
    assert classify_operator_intent(transcript) == expected


def test_agents_stop_api_requires_confirm(client):
    resp = client.post("/api/agents/stop", json={"confirmed": False})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "confirmation_required"


def test_agents_stop_and_restart_api(client):
    resp = client.post("/api/agents/stop", json={"confirmed": True})
    assert resp.status_code == 200
    assert resp.json()["paused"] is True

    resp2 = client.post("/api/agents/restart")
    assert resp2.status_code == 200
    assert resp2.json()["paused"] is False


def test_agents_control_status_api(client):
    resp = client.get("/api/agents/control")
    assert resp.status_code == 200
    assert "paused" in resp.json()