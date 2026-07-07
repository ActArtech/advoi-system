"""Decision frame catalog — PWA buttons and voice intents share these ids."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

FrameId = Literal["fleet_status", "open_briefs", "queue_deep_review"]


@dataclass(frozen=True)
class DecisionFrame:
    id: FrameId
    label: str
    agent_id: str
    voice_prompt: str
    requires_confirmation: bool = False


FRAMES: tuple[DecisionFrame, ...] = (
    DecisionFrame(
        id="fleet_status",
        label="Option A — Fleet status",
        agent_id="fleet-scout",
        voice_prompt="Give me a quick fleet status update.",
    ),
    DecisionFrame(
        id="open_briefs",
        label="Option B — Open briefs",
        agent_id="brief-curator",
        voice_prompt="What decision briefs are open right now?",
    ),
    DecisionFrame(
        id="queue_deep_review",
        label="Option C — Queue deep review",
        agent_id="review-queue",
        voice_prompt="Queue a deep review for the top priority item.",
        requires_confirmation=True,
    ),
)

FRAMES_BY_ID: dict[FrameId, DecisionFrame] = {f.id: f for f in FRAMES}


def get_frame(frame_id: str) -> DecisionFrame | None:
    return FRAMES_BY_ID.get(frame_id)  # type: ignore[arg-type]