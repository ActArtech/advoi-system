"""T0: Portfolio Event Log (PEL) — schema append + emit points (moat R1)."""

from __future__ import annotations

import pytest

from advoi.analytics.pel import (
    EventSource,
    EventType,
    GuardianStatus,
    append_event,
    memory_rows,
    reset_memory_store,
    transcript_hash,
)
from advoi.fleet.trigger import fleet_trigger_from_voice, invoke_fleet_trigger
from advoi.routing.frame_runner import run_frame
from advoi.voice.intent_processor import maybe_handle_frame_intent


@pytest.fixture(autouse=True)
def _pel_memory(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ADVOI_PEL_MEMORY", "true")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    reset_memory_store()
    yield
    reset_memory_store()


@pytest.mark.asyncio
async def test_append_event_creates_row():
    event_id = await append_event(
        venture_id="clapart",
        source=EventSource.FLEET,
        event_type=EventType.FLEET_TRIGGER,
        payload={"action": "arm", "status": "mock"},
        guardian_status=GuardianStatus.ALLOWED,
    )
    assert event_id is not None
    rows = memory_rows()
    assert len(rows) == 1
    assert rows[0]["id"] == event_id
    assert rows[0]["venture_id"] == "clapart"
    assert rows[0]["source"] == "fleet"
    assert rows[0]["type"] == "fleet_trigger"
    assert rows[0]["guardian_status"] == "allowed"
    assert rows[0]["payload"]["action"] == "arm"


@pytest.mark.asyncio
async def test_append_event_idempotent_on_legacy_key():
    first = await append_event(
        venture_id="advoi",
        source=EventSource.MEMORY,
        event_type=EventType.PORTFOLIO_FACT,
        payload={"summary": "once"},
        legacy_memory_event_id=42,
    )
    second = await append_event(
        venture_id="advoi",
        source=EventSource.MEMORY,
        event_type=EventType.PORTFOLIO_FACT,
        payload={"summary": "duplicate"},
        legacy_memory_event_id=42,
    )
    assert first is not None
    assert second == first
    rows = memory_rows()
    assert len(rows) == 1
    assert rows[0]["payload"]["summary"] == "once"


@pytest.mark.asyncio
async def test_append_event_distinct_without_legacy_key():
    await append_event(
        venture_id="advoi",
        source=EventSource.API,
        event_type=EventType.FRAME_RUN,
        payload={"n": 1},
    )
    await append_event(
        venture_id="advoi",
        source=EventSource.API,
        event_type=EventType.FRAME_RUN,
        payload={"n": 2},
    )
    assert len(memory_rows()) == 2


@pytest.mark.asyncio
async def test_emit_frame_run_row(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ADVOI_FRAME_MOCK", "true")
    result = await run_frame("fleet_status", refresh=True)
    assert result.status in {"ok", "error"}
    frame_rows = [r for r in memory_rows() if r["type"] == "frame_run"]
    assert len(frame_rows) >= 1
    row = frame_rows[-1]
    assert row["source"] == "api"
    assert row["payload"]["frame_id"] == "fleet_status"
    assert row["payload"]["agent_id"]
    assert "spoken_summary_len" in row["payload"]


@pytest.mark.asyncio
async def test_emit_fleet_trigger_row(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ADVOI_FLEET_MOCK", "true")
    result = await invoke_fleet_trigger("arm", project="clapart")
    assert result["ok"] is True
    rows = [r for r in memory_rows() if r["type"] == "fleet_trigger"]
    assert len(rows) == 1
    assert rows[0]["venture_id"] == "clapart"
    assert rows[0]["source"] == "fleet"
    assert rows[0]["payload"]["status"] == "mock"
    assert rows[0]["payload"]["mock"] is True
    assert rows[0]["guardian_status"] == "allowed"


@pytest.mark.asyncio
async def test_emit_fleet_confirmation_path(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ADVOI_CONFIRMATION_REQUIRED", "true")
    monkeypatch.setenv("ADVOI_FLEET_MOCK", "true")
    denied = await fleet_trigger_from_voice(
        "wake_firstmate",
        transcript="wake firstmate",
        confirmed=False,
    )
    assert denied["status"] == "confirmation_required"
    gate_rows = [r for r in memory_rows() if r["type"] == "guardian_gate"]
    assert len(gate_rows) == 1
    assert gate_rows[0]["guardian_status"] == "pending"
    assert gate_rows[0]["payload"]["proceed"] is False

    reset_memory_store()
    allowed = await fleet_trigger_from_voice(
        "wake_firstmate",
        transcript="wake firstmate confirm",
        confirmed=True,
    )
    assert allowed.get("ok") is True
    types = {r["type"] for r in memory_rows()}
    assert "guardian_gate" in types
    assert "fleet_trigger" in types
    gate = next(r for r in memory_rows() if r["type"] == "guardian_gate")
    assert gate["guardian_status"] == "allowed"
    trigger = next(r for r in memory_rows() if r["type"] == "fleet_trigger")
    assert trigger["venture_id"] == "clapart" or trigger["payload"].get("project")


@pytest.mark.asyncio
async def test_emit_voice_intent_frame_only(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ADVOI_FRAME_MOCK", "true")
    spoken: list[str] = []

    async def _speak(text: str) -> None:
        spoken.append(text)

    # Frame action → voice_intent + frame_run
    handled = await maybe_handle_frame_intent(
        "fleet status",
        session_id="pel-voice-1",
        speak=_speak,
    )
    assert handled is True
    assert spoken
    intent_rows = [r for r in memory_rows() if r["type"] == "voice_intent"]
    assert len(intent_rows) == 1
    assert intent_rows[0]["source"] == "voice"
    assert intent_rows[0]["payload"]["route"] == "frame"
    assert intent_rows[0]["payload"]["frame_id"] == "fleet_status"
    assert intent_rows[0]["payload"]["transcript_hash"] == transcript_hash("fleet status")

    # Chat-like non-frame transcript → no additional voice_intent
    reset_memory_store()
    handled_chat = await maybe_handle_frame_intent(
        "tell me a joke about weather",
        session_id="pel-voice-2",
        speak=_speak,
    )
    assert handled_chat is False
    assert memory_rows() == []


@pytest.mark.asyncio
async def test_emit_voice_operator_intent(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ADVOI_FLEET_MOCK", "true")
    monkeypatch.setenv("ADVOI_CONFIRMATION_REQUIRED", "true")
    spoken: list[str] = []

    async def _speak(text: str) -> None:
        spoken.append(text)

    handled = await maybe_handle_frame_intent(
        "wake firstmate",
        session_id="pel-voice-op",
        speak=_speak,
    )
    assert handled is True
    intent_rows = [r for r in memory_rows() if r["type"] == "voice_intent"]
    assert len(intent_rows) == 1
    assert intent_rows[0]["payload"]["route"] == "operator"
    assert intent_rows[0]["payload"]["intent_id"] == "wake_firstmate"
    assert intent_rows[0]["guardian_status"] == "pending"


def test_event_source_vocabulary():
    values = {s.value for s in EventSource}
    assert "voice" in values
    assert "fleet" in values
    assert "api" in values
    assert "memory" in values


def test_transcript_hash_stable():
    assert transcript_hash("hello") == transcript_hash("hello")
    assert transcript_hash("hello") != transcript_hash("world")
