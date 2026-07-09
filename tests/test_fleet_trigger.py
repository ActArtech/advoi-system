"""FirstMate fleet voice trigger bridge."""

import pytest

from advoi.fleet.bridge import fleet_bridge_script, resolve_fleet_exec
from advoi.fleet.session import clear_pending_fleet, get_pending_fleet, set_pending_fleet
from advoi.fleet.trigger import (
    classify_fleet_voice_intent,
    extract_project_slug,
    fleet_action_needs_confirm,
    fleet_trigger_from_voice,
    invoke_fleet_trigger,
)
from advoi.voice.capabilities import classify_operator_intent
from advoi.voice.respond import warm_spoken_reply


@pytest.mark.parametrize(
    "transcript,expected",
    [
        ("wake firstmate", "wake_firstmate"),
        ("arm fleet", "wake_firstmate"),
        ("start development on clapart", "start_development"),
        ("run next backlog", "run_next_backlog"),
        ("stop fleet", "fleet_stop"),
        ("fleet status", None),
    ],
)
def test_classify_fleet_voice_intent(transcript, expected):
    assert classify_fleet_voice_intent(transcript) == expected


def test_classify_operator_fleet_beats_firstmate_info():
    assert classify_operator_intent("wake firstmate") == "wake_firstmate"
    assert classify_operator_intent("start development on clapart") == "start_development"


def test_extract_project_slug():
    assert extract_project_slug("start development on clapart") == "clapart"
    assert extract_project_slug("wake firstmate") is None


@pytest.mark.asyncio
async def test_invoke_fleet_trigger_mock(monkeypatch):
    monkeypatch.setenv("ADVOI_FLEET_MOCK", "true")
    result = await invoke_fleet_trigger("arm", project="clapart")
    assert result["ok"] is True
    assert result["status"] == "mock"
    assert result["project"] == "clapart"


@pytest.mark.asyncio
async def test_fleet_confirm_gate():
    reply = await warm_spoken_reply("wake firstmate")
    assert reply.action == "confirmation_required"
    assert "confirm" in reply.spoken.lower()


@pytest.mark.asyncio
async def test_wake_firstmate_with_confirm(monkeypatch):
    monkeypatch.setenv("ADVOI_FLEET_MOCK", "true")
    monkeypatch.setenv("ADVOI_CONFIRMATION_REQUIRED", "true")
    reply = await warm_spoken_reply("wake firstmate confirm")
    assert reply.action == "wake_firstmate"
    assert "armed" in reply.spoken.lower() or "firstmate" in reply.spoken.lower()


@pytest.mark.asyncio
async def test_start_development_confirm(monkeypatch):
    monkeypatch.setenv("ADVOI_FLEET_MOCK", "true")
    monkeypatch.setenv("ADVOI_CONFIRMATION_REQUIRED", "true")
    reply = await warm_spoken_reply("start development on clapart confirm")
    assert reply.action == "start_development"
    assert "clapart" in reply.spoken.lower()


@pytest.mark.asyncio
async def test_fleet_trigger_api_requires_confirm(client):
    resp = client.post(
        "/api/fleet/trigger",
        json={"action": "wake_firstmate", "confirmed": False},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "confirmation_required"


@pytest.mark.asyncio
async def test_fleet_trigger_api_mock(client, monkeypatch):
    monkeypatch.setenv("ADVOI_FLEET_MOCK", "true")
    resp = client.post(
        "/api/fleet/trigger",
        json={"action": "wake_firstmate", "confirmed": True, "project": "clapart"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["action"] == "wake_firstmate"


def test_fleet_action_needs_confirm_respects_env(monkeypatch):
    monkeypatch.setenv("ADVOI_CONFIRMATION_REQUIRED", "false")
    assert fleet_action_needs_confirm("wake firstmate") is False
    monkeypatch.setenv("ADVOI_CONFIRMATION_REQUIRED", "true")
    assert fleet_action_needs_confirm("wake firstmate") is True
    assert fleet_action_needs_confirm("wake firstmate confirm") is False


def test_resolve_fleet_exec_prefers_bridge_script(monkeypatch, tmp_path):
    bridge = tmp_path / "fm-bridge.sh"
    bridge.write_text("#!/bin/bash\n", encoding="utf-8")
    monkeypatch.setenv("ADVOI_FM_BRIDGE_SCRIPT", str(bridge))
    assert fleet_bridge_script() == bridge
    assert resolve_fleet_exec() == ("bash", str(bridge))


@pytest.mark.asyncio
async def test_pending_fleet_yes_confirm(monkeypatch):
    monkeypatch.setenv("ADVOI_FLEET_MOCK", "true")
    monkeypatch.setenv("ADVOI_CONFIRMATION_REQUIRED", "true")
    session = "test-fleet-yes"
    clear_pending_fleet(session)

    reply1 = await warm_spoken_reply("wake firstmate", session_id=session)
    assert reply1.action == "confirmation_required"
    assert reply1.pending_operator == "wake_firstmate"
    assert get_pending_fleet(session) is not None

    reply2 = await warm_spoken_reply("yes", session_id=session)
    assert reply2.action == "wake_firstmate"
    assert get_pending_fleet(session) is None


def test_pending_fleet_session_helpers():
    clear_pending_fleet("s1")
    set_pending_fleet("s1", "run_next_backlog", "run next backlog")
    assert get_pending_fleet("s1") == ("run_next_backlog", "run next backlog")
    clear_pending_fleet("s1")
    assert get_pending_fleet("s1") is None