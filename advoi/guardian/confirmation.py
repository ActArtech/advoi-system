"""Confirmation harness — gate high-risk frames until explicit approval."""

from __future__ import annotations

import os

from advoi.decision.frames import get_frame
from advoi.routing.intent import is_confirm_phrase

_DEFAULT_PROMPT = "Confirm yes on voice or tap again to proceed."


def global_confirmation_enabled() -> bool:
    return os.getenv("ADVOI_CONFIRMATION_REQUIRED", "true").lower() in {"1", "true", "yes"}


def frame_needs_confirmation(frame_id: str) -> bool:
    frame = get_frame(frame_id)
    if not frame or not frame.requires_confirmation:
        return False
    return global_confirmation_enabled()


def confirmation_prompt(frame_id: str) -> str:
    frame = get_frame(frame_id)
    if frame and frame.requires_confirmation:
        return (
            f"To run {frame.label}, confirm yes on voice or tap again after reviewing."
        )
    return _DEFAULT_PROMPT


def evaluate_frame_confirmation(
    frame_id: str,
    *,
    confirmed: bool,
    transcript: str | None = None,
) -> dict[str, bool | str]:
    """Return whether a frame run may proceed and whether we are awaiting confirm."""
    explicit_confirm = confirmed or (bool(transcript) and is_confirm_phrase(transcript))
    if not frame_needs_confirmation(frame_id):
        return {"proceed": True, "awaiting_confirmation": False}
    if explicit_confirm:
        return {"proceed": True, "awaiting_confirmation": False}
    return {
        "proceed": False,
        "awaiting_confirmation": True,
        "prompt": confirmation_prompt(frame_id),
    }