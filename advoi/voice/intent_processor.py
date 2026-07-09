"""Route STT transcripts to decision frames in the LiveKit Pipecat pipeline."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from advoi.copy_style import plain_copy
from advoi.decision.frames import FrameId
from advoi.routing.frame_runner import run_frame
from advoi.routing.intent import is_confirm_phrase, resolve_voice_action
from advoi.voice.capabilities import classify_operator_intent
from advoi.voice.respond import _reply_operator_intent
from advoi.voice.memory_hooks import retain_turn

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
    else:
        clear_pending_frame(session_id)

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

    from advoi.voice.respond import _FLEET_WRITE_INTENTS, _stop_agents_needs_confirm
    from advoi.fleet.trigger import fleet_action_needs_confirm, fleet_confirm_prompt

    op = classify_operator_intent(text)
    if op == "stop_agents" and _stop_agents_needs_confirm(text):
        await speak("To pause background agent daemons, say stop agents confirm.")
        return True
    if op in _FLEET_WRITE_INTENTS and fleet_action_needs_confirm(text):
        await speak(fleet_confirm_prompt(op))
        return True
    if op:
        reply = await _reply_operator_intent(op, transcript=text)
        if reply:
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