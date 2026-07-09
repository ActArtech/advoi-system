"""Keyword intent routing from free-form voice transcripts to decision frames."""

from __future__ import annotations

import re
from typing import Literal, TypedDict

from advoi.decision.frames import FRAMES_BY_ID, FrameId, get_frame

# Phrase patterns checked first (most specific wins).
_PHRASE_PATTERNS: tuple[tuple[str, FrameId], ...] = (
    ("systems pulse", "systems_pulse"),
    ("system pulse", "systems_pulse"),
    ("systems status", "systems_pulse"),
    ("portfolio pulse", "systems_pulse"),
    ("memory health", "memory_health"),
    ("memory status", "memory_health"),
    ("guardian status", "guardian_status"),
    ("safety check", "guardian_status"),
    ("deep review", "queue_deep_review"),
    ("queue review", "queue_deep_review"),
    ("queue a review", "queue_deep_review"),
    ("queue deep", "queue_deep_review"),
    ("review queue", "queue_deep_review"),
    ("open briefs", "open_briefs"),
    ("open brief", "open_briefs"),
    ("decision brief", "open_briefs"),
    ("briefs open", "open_briefs"),
    ("fleet status", "fleet_status"),
    ("fleet update", "fleet_status"),
    ("fleet scout", "fleet_status"),
)

_KEYWORD_FRAMES: tuple[tuple[tuple[str, ...], FrameId], ...] = (
    (("pulse",), "systems_pulse"),
    (("guardian",), "guardian_status"),
    (("memory",), "memory_health"),
    (("brief", "briefs"), "open_briefs"),
    (("fleet",), "fleet_status"),
)

_CONFIRM_WORDS: frozenset[str] = frozenset(
    {
        "yes",
        "yeah",
        "yep",
        "confirm",
        "confirmed",
        "go ahead",
        "do it",
        "sure",
        "okay",
        "ok",
        "proceed",
        "approved",
    }
)


class VoiceFrameAction(TypedDict):
    action: Literal["frame"]
    frame_id: FrameId
    confirmed: bool


class VoiceChatAction(TypedDict):
    action: Literal["chat"]


VoiceAction = VoiceFrameAction | VoiceChatAction


def _normalize(transcript: str) -> str:
    return re.sub(r"\s+", " ", (transcript or "").strip().lower())


def _has_word(text: str, word: str) -> bool:
    return bool(re.search(rf"\b{re.escape(word)}\b", text, re.IGNORECASE))


def _detect_confirmation(text: str) -> bool:
    return any(_has_word(text, word) for word in _CONFIRM_WORDS)


def is_confirm_phrase(transcript: str) -> bool:
    """Return True when the transcript is a short confirmation (yes, go ahead, etc.)."""
    return _detect_confirmation(_normalize(transcript))


def classify_transcript(transcript: str) -> FrameId | None:
    """Map a voice transcript to a decision frame id, or None for general chat."""
    text = _normalize(transcript)
    if not text:
        return None

    for phrase, frame_id in _PHRASE_PATTERNS:
        if phrase in text:
            return frame_id

    for keywords, frame_id in _KEYWORD_FRAMES:
        if any(_has_word(text, keyword) for keyword in keywords):
            return frame_id

    if _has_word(text, "queue"):
        return "queue_deep_review"

    return None


def resolve_voice_action(transcript: str) -> VoiceAction:
    """Resolve transcript to a frame action or fall back to open chat."""
    text = _normalize(transcript)
    frame_id = classify_transcript(text)
    if not frame_id:
        return VoiceChatAction(action="chat")

    frame = get_frame(frame_id)
    confirmed = _detect_confirmation(text)
    if frame and frame.requires_confirmation:
        return VoiceFrameAction(action="frame", frame_id=frame_id, confirmed=confirmed)

    return VoiceFrameAction(action="frame", frame_id=frame_id, confirmed=True)


def frame_intent_label(frame_id: FrameId) -> str:
    """Human label for API responses."""
    frame = FRAMES_BY_ID[frame_id]
    return frame.label