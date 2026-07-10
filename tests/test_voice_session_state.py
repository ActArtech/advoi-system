"""Unit tests for PWA voice UI state machine (mirrors web/components/voiceSessionState.ts).

Python port keeps CI green without a JS test runner. Keep transitions in sync with the TS reducer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

UiSessionState = Literal[
    "idle",
    "connecting",
    "connected",
    "frame_running",
    "confirm_pending",
    "error",
]

UI_STATE_LABELS: dict[str, str] = {
    "idle": "Idle",
    "connecting": "Connecting",
    "connected": "Connected",
    "frame_running": "Frame running",
    "confirm_pending": "Confirm pending",
    "error": "Error",
}

UI_SESSION_STATES = (
    "idle",
    "connecting",
    "connected",
    "frame_running",
    "confirm_pending",
    "error",
)


@dataclass(frozen=True)
class Ctx:
    state: UiSessionState
    voice_connected: bool


INITIAL = Ctx(state="idle", voice_connected=False)


def reduce(ctx: Ctx, event: str) -> Ctx:
    """Mirror of reduceUiSession in voiceSessionState.ts."""
    if event == "CONNECT_START":
        if ctx.state in ("frame_running", "confirm_pending"):
            return ctx
        return Ctx(state="connecting", voice_connected=ctx.voice_connected)
    if event == "CONNECT_OK":
        if ctx.state in ("frame_running", "confirm_pending"):
            return Ctx(state=ctx.state, voice_connected=True)
        return Ctx(state="connected", voice_connected=True)
    if event == "CONNECT_FAIL":
        return Ctx(state="error", voice_connected=False)
    if event == "DISCONNECT":
        return Ctx(state="idle", voice_connected=False)
    if event == "FRAME_START":
        return Ctx(state="frame_running", voice_connected=ctx.voice_connected)
    if event == "CONFIRMATION_REQUIRED":
        return Ctx(state="confirm_pending", voice_connected=ctx.voice_connected)
    if event == "FRAME_OK":
        return Ctx(
            state="connected" if ctx.voice_connected else "idle",
            voice_connected=ctx.voice_connected,
        )
    if event == "FRAME_FAIL_KEEP_VOICE":
        if ctx.voice_connected:
            return Ctx(state="connected", voice_connected=True)
        return Ctx(state="error", voice_connected=False)
    if event == "ERROR":
        return Ctx(state="error", voice_connected=ctx.voice_connected)
    if event == "RESET_IDLE":
        return Ctx(
            state="connected" if ctx.voice_connected else "idle",
            voice_connected=ctx.voice_connected,
        )
    return ctx


def test_six_states_and_labels():
    assert list(UI_SESSION_STATES) == [
        "idle",
        "connecting",
        "connected",
        "frame_running",
        "confirm_pending",
        "error",
    ]
    for s in UI_SESSION_STATES:
        assert UI_STATE_LABELS[s]


def test_livekit_connect_path():
    ctx = INITIAL
    ctx = reduce(ctx, "CONNECT_START")
    assert ctx.state == "connecting"
    assert ctx.voice_connected is False
    ctx = reduce(ctx, "CONNECT_OK")
    assert ctx.state == "connected"
    assert ctx.voice_connected is True
    ctx = reduce(ctx, "DISCONNECT")
    assert ctx == INITIAL


def test_livekit_connect_fail():
    ctx = reduce(INITIAL, "CONNECT_START")
    ctx = reduce(ctx, "CONNECT_FAIL")
    assert ctx.state == "error"
    assert ctx.voice_connected is False


def test_frame_run_without_voice():
    ctx = reduce(INITIAL, "FRAME_START")
    assert ctx.state == "frame_running"
    ctx = reduce(ctx, "FRAME_OK")
    assert ctx.state == "idle"


def test_frame_run_with_voice():
    ctx = reduce(INITIAL, "CONNECT_OK")
    ctx = reduce(ctx, "FRAME_START")
    assert ctx.state == "frame_running"
    assert ctx.voice_connected is True
    ctx = reduce(ctx, "FRAME_OK")
    assert ctx.state == "connected"


def test_guardian_confirmation_required():
    ctx = reduce(INITIAL, "CONNECT_OK")
    ctx = reduce(ctx, "FRAME_START")
    ctx = reduce(ctx, "CONFIRMATION_REQUIRED")
    assert ctx.state == "confirm_pending"
    assert ctx.voice_connected is True
    # User confirms → frame runs again → ok
    ctx = reduce(ctx, "FRAME_START")
    assert ctx.state == "frame_running"
    ctx = reduce(ctx, "FRAME_OK")
    assert ctx.state == "connected"


def test_confirmation_without_voice():
    ctx = reduce(INITIAL, "FRAME_START")
    ctx = reduce(ctx, "CONFIRMATION_REQUIRED")
    assert ctx.state == "confirm_pending"
    ctx = reduce(ctx, "FRAME_OK")
    assert ctx.state == "idle"


def test_frame_fail_keeps_voice_when_connected():
    ctx = reduce(INITIAL, "CONNECT_OK")
    ctx = reduce(ctx, "FRAME_START")
    ctx = reduce(ctx, "FRAME_FAIL_KEEP_VOICE")
    assert ctx.state == "connected"
    assert ctx.voice_connected is True


def test_frame_fail_errors_when_idle_transport():
    ctx = reduce(INITIAL, "FRAME_START")
    ctx = reduce(ctx, "FRAME_FAIL_KEEP_VOICE")
    assert ctx.state == "error"


def test_connect_ok_preserves_frame_running():
    ctx = reduce(INITIAL, "FRAME_START")
    ctx = reduce(ctx, "CONNECT_OK")
    assert ctx.state == "frame_running"
    assert ctx.voice_connected is True
