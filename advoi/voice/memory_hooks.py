"""Retain voice turns to Redis (and rolling summary) during Pipecat pipeline."""

from __future__ import annotations

import logging
from typing import Any

from advoi.memory import MemoryRouter
from advoi.memory.write_targets import MemoryEventType

_LOGGER = logging.getLogger(__name__)


async def retain_turn(*, session_id: str, role: str, text: str) -> None:
    text = (text or "").strip()
    if not text:
        return
    router = MemoryRouter()
    payload: dict[str, Any] = {"role": role, "text": text, "summary": text[:500]}
    results = await router.retain(
        MemoryEventType.VOICE_TURN,
        payload,
        session_id=session_id,
    )
    _LOGGER.debug("voice retain %s: %s", role, results)


def build_memory_processor(session_id: str):
    """Pipecat processor that retains user transcriptions and assistant text."""
    from pipecat.frames.frames import (
        Frame,
        LLMTextFrame,
        TranscriptionFrame,
    )
    from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

    class VoiceMemoryProcessor(FrameProcessor):
        async def process_frame(self, frame: Frame, direction: FrameDirection):
            await super().process_frame(frame, direction)
            try:
                if isinstance(frame, TranscriptionFrame) and frame.text:
                    await retain_turn(session_id=session_id, role="user", text=frame.text)
                elif isinstance(frame, LLMTextFrame) and frame.text:
                    await retain_turn(session_id=session_id, role="assistant", text=frame.text)
            except Exception as exc:
                _LOGGER.debug("memory hook skip: %s", exc)
            await self.push_frame(frame, direction)

    return VoiceMemoryProcessor()