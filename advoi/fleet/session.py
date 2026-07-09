"""Per-session pending FirstMate fleet confirmations (voice two-step)."""

from __future__ import annotations

from advoi.fleet.trigger import FleetVoiceAction

_pending: dict[str, tuple[FleetVoiceAction, str]] = {}


def set_pending_fleet(
    session_id: str,
    action: FleetVoiceAction,
    transcript: str,
) -> None:
    _pending[session_id] = (action, transcript)


def get_pending_fleet(session_id: str) -> tuple[FleetVoiceAction, str] | None:
    return _pending.get(session_id)


def clear_pending_fleet(session_id: str) -> None:
    _pending.pop(session_id, None)