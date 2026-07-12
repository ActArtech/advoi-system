"""FirstMate fleet voice trigger bridge."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from advoi.fleet.bridge import fleet_bridge_script, resolve_fleet_exec
from advoi.fleet.session import clear_pending_fleet, get_pending_fleet, set_pending_fleet
from advoi.fleet.trigger import (
    FLEET_ACTION_BRIDGE_VERB,
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
    # Low-level invoke requires explicit post-gate token when confirmation is on.
    result = await invoke_fleet_trigger(
        "arm",
        project="clapart",
        guardian_allowed=True,
    )
    assert result["ok"] is True
    assert result["status"] == "mock"
    assert result["project"] == "clapart"


@pytest.mark.asyncio
async def test_invoke_fleet_trigger_requires_guardian_when_confirmation_on(monkeypatch):
    monkeypatch.setenv("ADVOI_FLEET_MOCK", "true")
    monkeypatch.setenv("ADVOI_CONFIRMATION_REQUIRED", "true")
    denied = await invoke_fleet_trigger("arm", project="clapart")
    assert denied["ok"] is False
    assert denied["status"] == "guardian_required"
    assert denied.get("guardian") is True


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


def test_fleet_action_needs_confirm_respects_transcript():
    assert fleet_action_needs_confirm("wake firstmate") is True
    assert fleet_action_needs_confirm("wake firstmate confirm") is False
    assert fleet_action_needs_confirm("yes") is False


@pytest.mark.asyncio
async def test_start_development_guardian_gate(monkeypatch):
    monkeypatch.setenv("ADVOI_CONFIRMATION_REQUIRED", "true")
    result = await fleet_trigger_from_voice(
        "start_development",
        transcript="start development on clapart",
        confirmed=False,
    )
    assert result["status"] == "confirmation_required"
    assert result.get("guardian") is True


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


def test_wake_firstmate_maps_to_arm_bridge_verb():
    """Durable contract: operator wake_firstmate / arm fleet → hermes verb ``arm``."""
    assert FLEET_ACTION_BRIDGE_VERB["wake_firstmate"] == "arm"
    assert FLEET_ACTION_BRIDGE_VERB["fleet_stop"] == "stop"
    assert classify_fleet_voice_intent("arm fleet") == "wake_firstmate"
    assert classify_fleet_voice_intent("wake firstmate") == "wake_firstmate"


def _mock_proc(*, returncode: int = 0, stdout: bytes = b"OK: fleet arm") -> MagicMock:
    proc = MagicMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout, None))
    return proc


@pytest.mark.asyncio
async def test_wake_firstmate_reaches_bridge_with_arm_env_args(monkeypatch, tmp_path):
    """T0: confirmed wake_firstmate shells fm-bridge with arm + FM_HERMES_PROJECT."""
    monkeypatch.delenv("ADVOI_FLEET_MOCK", raising=False)
    monkeypatch.setenv("ADVOI_FLEET_MOCK", "false")
    monkeypatch.setenv("ADVOI_CONFIRMATION_REQUIRED", "true")
    monkeypatch.setenv("ADVOI_PEL_MEMORY", "true")

    bridge = tmp_path / "fm-bridge.sh"
    bridge.write_text("#!/bin/bash\necho mock\n", encoding="utf-8")
    monkeypatch.setenv("ADVOI_FM_BRIDGE_SCRIPT", str(bridge))

    mock_exec = AsyncMock(return_value=_mock_proc(stdout=b"OK: fleet arm - continuous loop"))
    with patch("asyncio.create_subprocess_exec", mock_exec):
        result = await fleet_trigger_from_voice(
            "wake_firstmate",
            transcript="wake firstmate on clapart confirm",
            confirmed=True,
        )

    assert result["ok"] is True
    assert result["status"] == "dispatched"
    assert result["action"] == "wake_firstmate"
    assert result["message"] == "arm"
    assert result["project"] == "clapart"
    assert result["bridge"] == str(bridge)

    mock_exec.assert_awaited_once()
    call_args = mock_exec.await_args
    # argv: bash + bridge + message
    assert call_args.args[0] == "bash"
    assert call_args.args[1] == str(bridge)
    assert call_args.args[2] == "arm"
    env = call_args.kwargs["env"]
    assert env["FM_HERMES_PROJECT"] == "clapart"
    assert env.get("FIRSTMATE_CONTAINER") == "firstmate-fleet" or "FIRSTMATE_CONTAINER" in env


@pytest.mark.asyncio
async def test_arm_fleet_voice_path_reaches_bridge(monkeypatch, tmp_path):
    """T0: 'arm fleet' intent → same arm verb on bridge after confirm."""
    monkeypatch.setenv("ADVOI_FLEET_MOCK", "false")
    monkeypatch.setenv("ADVOI_CONFIRMATION_REQUIRED", "true")
    monkeypatch.setenv("ADVOI_PEL_MEMORY", "true")

    bridge = tmp_path / "fm-bridge.sh"
    bridge.write_text("#!/bin/bash\n", encoding="utf-8")
    monkeypatch.setenv("ADVOI_FM_BRIDGE_SCRIPT", str(bridge))

    mock_exec = AsyncMock(return_value=_mock_proc())
    with patch("asyncio.create_subprocess_exec", mock_exec):
        result = await fleet_trigger_from_voice(
            "wake_firstmate",
            transcript="arm fleet on clapart confirm",
            confirmed=True,
        )

    assert result["ok"] is True
    assert result["message"] == "arm"
    assert mock_exec.await_args.args[2] == "arm"
    assert mock_exec.await_args.kwargs["env"]["FM_HERMES_PROJECT"] == "clapart"


@pytest.mark.asyncio
async def test_wake_firstmate_confirmation_off_path_no_subprocess(monkeypatch, tmp_path):
    """T0: unconfirmed wake returns confirmation_required; never shells bridge."""
    monkeypatch.setenv("ADVOI_FLEET_MOCK", "false")
    monkeypatch.setenv("ADVOI_CONFIRMATION_REQUIRED", "true")
    monkeypatch.setenv("ADVOI_PEL_MEMORY", "true")

    bridge = tmp_path / "fm-bridge.sh"
    bridge.write_text("#!/bin/bash\n", encoding="utf-8")
    monkeypatch.setenv("ADVOI_FM_BRIDGE_SCRIPT", str(bridge))

    mock_exec = AsyncMock(return_value=_mock_proc())
    with patch("asyncio.create_subprocess_exec", mock_exec):
        result = await fleet_trigger_from_voice(
            "wake_firstmate",
            transcript="wake firstmate",
            confirmed=False,
        )

    assert result["ok"] is False
    assert result["status"] == "confirmation_required"
    assert result.get("guardian") is True
    mock_exec.assert_not_called()


@pytest.mark.asyncio
async def test_invoke_guardian_required_skips_subprocess(monkeypatch, tmp_path):
    """T0: bare invoke without Guardian token → guardian_required, no shell."""
    monkeypatch.setenv("ADVOI_FLEET_MOCK", "false")
    monkeypatch.setenv("ADVOI_CONFIRMATION_REQUIRED", "true")
    monkeypatch.setenv("ADVOI_PEL_MEMORY", "true")

    bridge = tmp_path / "fm-bridge.sh"
    bridge.write_text("#!/bin/bash\n", encoding="utf-8")
    monkeypatch.setenv("ADVOI_FM_BRIDGE_SCRIPT", str(bridge))

    mock_exec = AsyncMock(return_value=_mock_proc())
    with patch("asyncio.create_subprocess_exec", mock_exec):
        denied = await invoke_fleet_trigger("arm", project="clapart")

    assert denied["ok"] is False
    assert denied["status"] == "guardian_required"
    assert denied.get("guardian") is True
    mock_exec.assert_not_called()


@pytest.mark.asyncio
async def test_wake_firstmate_uses_session_after_portfolio_active(client, monkeypatch):
    """portfolio/active session override feeds fleet trigger when project omitted."""
    from advoi.portfolio.ecr import clear_session_active_venture

    clear_session_active_venture()
    monkeypatch.setenv("ADVOI_FLEET_MOCK", "true")

    activate = client.post(
        "/api/portfolio/active",
        json={"venture_id": "advoi-system"},
    )
    assert activate.status_code == 200

    resp = client.post(
        "/api/fleet/trigger",
        json={"action": "wake_firstmate", "confirmed": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["project"] == "advoi"
    assert data["action"] == "wake_firstmate"


@pytest.mark.asyncio
async def test_wake_firstmate_uses_session_venture_slug(monkeypatch):
    """Session ECR override resolves fleet project without on-slug in transcript."""
    from advoi.portfolio.ecr import clear_session_active_venture, set_session_active_venture

    clear_session_active_venture()
    set_session_active_venture("advoi-system")
    monkeypatch.setenv("ADVOI_FLEET_MOCK", "true")
    monkeypatch.setenv("ADVOI_CONFIRMATION_REQUIRED", "true")

    result = await fleet_trigger_from_voice(
        "wake_firstmate",
        transcript="wake firstmate confirm",
        confirmed=True,
    )
    assert result["ok"] is True
    assert result["project"] == "advoi"
    assert result["action"] == "wake_firstmate"


@pytest.mark.asyncio
async def test_wake_firstmate_api_reaches_bridge(client, monkeypatch, tmp_path):
    """T0: POST /api/fleet/trigger wake_firstmate confirmed → bridge arm."""
    monkeypatch.setenv("ADVOI_FLEET_MOCK", "false")
    monkeypatch.setenv("ADVOI_CONFIRMATION_REQUIRED", "true")
    monkeypatch.setenv("ADVOI_PEL_MEMORY", "true")

    bridge = tmp_path / "fm-bridge.sh"
    bridge.write_text("#!/bin/bash\n", encoding="utf-8")
    monkeypatch.setenv("ADVOI_FM_BRIDGE_SCRIPT", str(bridge))

    mock_exec = AsyncMock(return_value=_mock_proc(stdout=b"OK: fleet arm"))
    with patch("asyncio.create_subprocess_exec", mock_exec):
        resp = client.post(
            "/api/fleet/trigger",
            json={
                "action": "wake_firstmate",
                "confirmed": True,
                "project": "clapart",
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["action"] == "wake_firstmate"
    assert data["message"] == "arm"
    mock_exec.assert_awaited_once()
    assert mock_exec.await_args.args == ("bash", str(bridge), "arm")
    assert mock_exec.await_args.kwargs["env"]["FM_HERMES_PROJECT"] == "clapart"