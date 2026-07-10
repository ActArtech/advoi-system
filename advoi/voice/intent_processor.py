"""Route STT transcripts to decision frames in the LiveKit Pipecat pipeline."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from advoi.copy_style import plain_copy
from advoi.decision.frames import FrameId
from advoi.routing.frame_runner import run_frame
from advoi.routing.intent import is_confirm_phrase, resolve_voice_action
from advoi.voice.capabilities import classify_operator_intent
from advoi.voice.memory_hooks import retain_turn
from advoi.voice.respond import _reply_operator_intent

_LOGGER = logging.getLogger(__name__)

SpeakCallback = Callable[[str], Awaitable[None]]

# Per-session pending frame awaiting voice confirmation (mirrors VoiceLoop pendingFrame).
_pending_frame_by_session: dict[str, FrameId] = {}


def get_pending_frame(session_id: str) -> FrameId | None:
    """Return the frame id awaiting confirmation for this session, if any."""
    return _pending_frame_by_session.get(session_id)


def clear_pending_frame(session_id: str) -> None:
    """Drop any pending confirmation for this session."""
    _pending_frame_by_session.pop(session_id, None)


def _set_pending_frame(session_id: str, frame_id: FrameId) -> None:
    _pending_frame_by_session[session_id] = frame_id


async def _emit_voice_intent(
    *,
    transcript: str,
    route: str,
    confirmed: bool,
    frame_id: str | None = None,
    intent_id: str | None = None,
    guardian_status: str | None = None,
    venture_id: str = "advoi",
    extra: dict[str, Any] | None = None,
) -> None:
    """PEL row for resolved frame/operator intents only — not every Redis voice turn."""
    from advoi.analytics.pel import (
        EventSource,
        EventType,
        safe_append_event,
        transcript_hash,
    )

    payload: dict[str, Any] = {
        "route": route,
        "confirmed": confirmed,
        "transcript_hash": transcript_hash(transcript),
        "transcript_excerpt": (transcript or "").strip()[:80],
    }
    if frame_id:
        payload["frame_id"] = frame_id
    if intent_id:
        payload["intent_id"] = intent_id
    if extra:
        payload.update(extra)

    await safe_append_event(
        venture_id=venture_id,
        source=EventSource.VOICE,
        event_type=EventType.VOICE_INTENT,
        payload=payload,
        guardian_status=guardian_status,
    )


async def _run_and_speak_frame(
    frame_id: FrameId,
    *,
    confirmed: bool,
    session_id: str,
    transcript: str,
    speak: SpeakCallback,
) -> None:
    result = await run_frame(frame_id, confirmed=confirmed)
    spoken = plain_copy(result.spoken_summary)
    _LOGGER.info(
        "voice intent frame=%s confirmed=%s status=%s pending_cleared=%s",
        frame_id,
        confirmed,
        result.status,
        result.status != "confirmation_required",
    )

    if result.status == "confirmation_required":
        _set_pending_frame(session_id, frame_id)
        guardian_status = "pending"
    else:
        clear_pending_frame(session_id)
        guardian_status = "allowed" if confirmed else "not_required"

    await _emit_voice_intent(
        transcript=transcript,
        route="frame",
        confirmed=confirmed,
        frame_id=str(frame_id),
        guardian_status=guardian_status,
    )

    try:
        await retain_turn(session_id=session_id, role="user", text=transcript)
        await retain_turn(session_id=session_id, role="assistant", text=spoken)
    except Exception as exc:
        _LOGGER.debug("voice frame retain skip: %s", exc)

    await speak(spoken)


async def maybe_handle_frame_intent(
    transcript: str,
    *,
    session_id: str,
    speak: SpeakCallback,
) -> bool:
    """Run a decision frame for frame intents; return True if LLM should be skipped."""
    text = (transcript or "").strip()
    if not text:
        return False

    from advoi.fleet.session import (
        clear_pending_fleet,
        get_pending_fleet,
        set_pending_fleet,
    )
    from advoi.guardian.confirmation import evaluate_fleet_confirmation
    from advoi.voice.respond import _FLEET_WRITE_INTENTS, _stop_agents_needs_confirm

    pending_fleet = get_pending_fleet(session_id)
    if pending_fleet and is_confirm_phrase(text):
        action, prior = pending_fleet
        clear_pending_fleet(session_id)
        reply = await _reply_operator_intent(
            action,
            transcript=f"{prior} confirm",
            confirmed=True,
        )
        if reply:
            await _emit_voice_intent(
                transcript=text,
                route="operator",
                confirmed=True,
                intent_id=action,
                guardian_status="allowed",
                extra={"prior_transcript_excerpt": (prior or "")[:80]},
            )
            try:
                await retain_turn(session_id=session_id, role="user", text=text)
                await retain_turn(session_id=session_id, role="assistant", text=reply.spoken)
            except Exception as exc:
                _LOGGER.debug("voice fleet confirm retain skip: %s", exc)
            await speak(reply.spoken)
            return True

    op = classify_operator_intent(text)
    if op == "stop_agents" and _stop_agents_needs_confirm(text):
        await _emit_voice_intent(
            transcript=text,
            route="operator",
            confirmed=False,
            intent_id=op,
            guardian_status="pending",
        )
        await speak("To pause background agent daemons, say stop agents confirm.")
        return True
    if op in _FLEET_WRITE_INTENTS:
        gate = evaluate_fleet_confirmation(op, confirmed=False, transcript=text)
        if not gate["proceed"]:
            set_pending_fleet(session_id, op, text)
            await _emit_voice_intent(
                transcript=text,
                route="operator",
                confirmed=False,
                intent_id=op,
                guardian_status="pending",
            )
            await speak(str(gate.get("prompt", "Confirm yes to proceed.")))
            return True
    if op:
        fleet_confirmed = True
        if op in _FLEET_WRITE_INTENTS:
            gate = evaluate_fleet_confirmation(op, confirmed=False, transcript=text)
            fleet_confirmed = bool(gate["proceed"])
        reply = await _reply_operator_intent(
            op,
            transcript=text,
            confirmed=fleet_confirmed,
        )
        if reply:
            await _emit_voice_intent(
                transcript=text,
                route="operator",
                confirmed=fleet_confirmed,
                intent_id=op,
                guardian_status="allowed" if fleet_confirmed else "pending",
            )
            try:
                await retain_turn(session_id=session_id, role="user", text=text)
                await retain_turn(session_id=session_id, role="assistant", text=reply.spoken)
            except Exception as exc:
                _LOGGER.debug("voice operator retain skip: %s", exc)
            await speak(reply.spoken)
            return True

    pending_frame = get_pending_frame(session_id)
    if pending_frame and is_confirm_phrase(text):
        await _run_and_speak_frame(
            pending_frame,
            confirmed=True,
            session_id=session_id,
            transcript=text,
            speak=speak,
        )
        return True

    action = resolve_voice_action(text)
    if action["action"] != "frame":
        return False

    await _run_and_speak_frame(
        action["frame_id"],
        confirmed=action["confirmed"],
        session_id=session_id,
        transcript=text,
        speak=speak,
    )
    return True


def build_intent_processor(*, session_id: str, speak: SpeakCallback):
    """Pipecat processor that bypasses the LLM when a transcript maps to a frame."""
    from pipecat.frames.frames import InterimTranscriptionFrame, TranscriptionFrame
    from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

    class VoiceIntentProcessor(FrameProcessor):
        async def process_frame(self, frame, direction: FrameDirection):
            await super().process_frame(frame, direction)

            if isinstance(frame, TranscriptionFrame) and not isinstance(
                frame, InterimTranscriptionFrame
            ):
                try:
                    handled = await maybe_handle_frame_intent(
                        frame.text,
                        session_id=session_id,
                        speak=speak,
                    )
                except Exception as exc:
                    _LOGGER.warning("voice frame intent failed: %s", exc)
                    await self.push_frame(frame, direction)
                    return

                if handled:
                    return

            await self.push_frame(frame, direction)

    return VoiceIntentProcessor()
