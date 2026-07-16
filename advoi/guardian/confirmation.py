"""Confirmation harness — gate high-risk frames and fleet writes until explicit approval."""

from __future__ import annotations

import os
from typing import Literal

from advoi.decision.frames import get_frame
from advoi.routing.intent import is_confirm_phrase

_DEFAULT_PROMPT = "Say go, yes, or tap Confirm to proceed."

FleetVoiceAction = Literal[
    "wake_firstmate",
    "start_development",
    "run_next_backlog",
    "fleet_stop",
]

HIGH_RISK_FLEET_ACTIONS: frozenset[FleetVoiceAction] = frozenset(
    {
        "wake_firstmate",
        "start_development",
        "run_next_backlog",
        "fleet_stop",
    }
)

_FLEET_CONFIRM_PROMPTS: dict[FleetVoiceAction, str] = {
    "wake_firstmate": (
        "Wake FirstMate will arm the fleet loop. Say go, yes, or tap Confirm."
    ),
    "start_development": (
        "Start development will arm the fleet and pick up work. Say go, yes, or tap Confirm."
    ),
    "run_next_backlog": (
        "This dispatches the next backlog item to FirstMate. Say go, yes, or tap Confirm."
    ),
    "fleet_stop": "This stops the FirstMate fleet loop. Say go, yes, or tap Confirm.",
}


def global_confirmation_enabled() -> bool:
    return os.getenv("ADVOI_CONFIRMATION_REQUIRED", "true").lower() in {"1", "true", "yes"}


def transcript_has_explicit_confirm(transcript: str | None) -> bool:
    if not transcript:
        return False
    lowered = transcript.lower().strip()
    if is_confirm_phrase(lowered):
        return True
    # Embedded confirms (e.g. "wake firstmate confirm", "yes go ahead").
    return any(
        w in lowered
        for w in (
            "confirm",
            "confirmed",
            "yes go ahead",
            " go ",
            " go.",
            "go ahead",
            "go on",
            "ship it",
        )
    ) or lowered.endswith(" go") or lowered == "go"


def frame_needs_confirmation(frame_id: str) -> bool:
    frame = get_frame(frame_id)
    if not frame or not frame.requires_confirmation:
        return False
    return global_confirmation_enabled()


def fleet_action_needs_confirmation(action: str) -> bool:
    if action not in HIGH_RISK_FLEET_ACTIONS:
        return False
    return global_confirmation_enabled()


def high_risk_fleet_actions() -> list[FleetVoiceAction]:
    return [action for action in HIGH_RISK_FLEET_ACTIONS if fleet_action_needs_confirmation(action)]


def confirmation_prompt(frame_id: str) -> str:
    frame = get_frame(frame_id)
    if frame and frame.requires_confirmation:
        return (
            f"To run {frame.label}, say go or yes, or tap Confirm after reviewing."
        )
    return _DEFAULT_PROMPT


def fleet_confirmation_prompt(action: str) -> str:
    if action in _FLEET_CONFIRM_PROMPTS:
        return _FLEET_CONFIRM_PROMPTS[action]  # type: ignore[index]
    return _DEFAULT_PROMPT


def evaluate_frame_confirmation(
    frame_id: str,
    *,
    confirmed: bool,
    transcript: str | None = None,
) -> dict[str, bool | str]:
    """Return whether a frame run may proceed and whether we are awaiting confirm."""
    explicit_confirm = confirmed or transcript_has_explicit_confirm(transcript)
    if not frame_needs_confirmation(frame_id):
        return {"proceed": True, "awaiting_confirmation": False}
    if explicit_confirm:
        return {"proceed": True, "awaiting_confirmation": False}
    return {
        "proceed": False,
        "awaiting_confirmation": True,
        "prompt": confirmation_prompt(frame_id),
    }


def evaluate_fleet_confirmation(
    action: str,
    *,
    confirmed: bool = False,
    transcript: str | None = None,
) -> dict[str, bool | str]:
    """Guardian gate for FirstMate fleet write intents (voice, API, ingestion)."""
    explicit_confirm = confirmed or transcript_has_explicit_confirm(transcript)
    if not fleet_action_needs_confirmation(action):
        return {"proceed": True, "awaiting_confirmation": False}
    if explicit_confirm:
        return {"proceed": True, "awaiting_confirmation": False}
    return {
        "proceed": False,
        "awaiting_confirmation": True,
        "prompt": fleet_confirmation_prompt(action),
    }