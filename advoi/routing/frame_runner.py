"""Execute decision frames via specialist agents."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Any

from advoi.decision.frames import DecisionFrame, get_frame
from advoi.memory import MemoryRouter
from advoi.routing.agents import AGENTS


@dataclass
class FrameResult:
    frame_id: str
    agent_id: str
    status: str
    spoken_summary: str
    detail: dict[str, Any]


async def _run_fleet_scout() -> tuple[str, dict[str, Any]]:
    if os.getenv("ADVOI_FRAME_MOCK", "").lower() in {"1", "true", "yes"}:
        return (
            "Fleet mock: Hermes and FirstMate runners look healthy. Two projects idle.",
            {"mode": "mock", "projects_idle": 2},
        )

    script = os.getenv(
        "FIRSTMATE_TRIGGER_SCRIPT",
        "/opt/firstmate-fleet/scripts/fm-hermes-trigger.sh",
    )
    msg = "fleet status"
    try:
        proc = await asyncio.create_subprocess_exec(
            "bash",
            script,
            msg,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=45)
        text = (stdout or stderr).decode("utf-8", errors="replace").strip()
        if not text:
            text = "Fleet bridge returned no output."
        # Keep voice-friendly — first ~3 sentences
        parts = [p.strip() for p in text.replace("\n", " ").split(". ") if p.strip()]
        spoken = ". ".join(parts[:3])
        if spoken and not spoken.endswith("."):
            spoken += "."
        return spoken or text[:400], {"exit_code": proc.returncode, "raw_preview": text[:500]}
    except asyncio.TimeoutError:
        return "Fleet status timed out. Try again in a moment.", {"error": "timeout"}
    except FileNotFoundError:
        return (
            "Fleet bridge is not configured on this host yet.",
            {"error": "missing_script", "script": script},
        )


async def _run_brief_curator() -> tuple[str, dict[str, Any]]:
    if os.getenv("ADVOI_FRAME_MOCK", "").lower() in {"1", "true", "yes"}:
        return (
            "You have two open briefs: ADVoi voice launch and staging catch-up.",
            {"mode": "mock", "briefs": ["ADVoi voice launch", "staging catch-up"]},
        )

    router = MemoryRouter()
    recall = await router.recall(session_id="voice-main", query="open decision briefs portfolio")
    items: list[str] = []
    for bucket in (recall.strategic, recall.operational, recall.ephemeral):
        for item in bucket[:3]:
            text = item.get("text") or item.get("summary") or item.get("content")
            if text:
                items.append(str(text)[:120])
    if items:
        spoken = "Open briefs from memory: " + "; ".join(items[:3])
        return spoken, {"briefs": items}
    return (
        "No briefs in memory yet. Say what you want captured and I'll log it after confirm.",
        {"briefs": []},
    )


async def _run_review_queue(*, confirmed: bool) -> tuple[str, dict[str, Any]]:
    if not confirmed and os.getenv("ADVOI_CONFIRMATION_REQUIRED", "true").lower() == "true":
        return (
            "To queue a deep review, confirm yes on voice or tap again after reviewing.",
            {"awaiting_confirmation": True},
        )
    if os.getenv("ADVOI_FRAME_MOCK", "").lower() in {"1", "true", "yes"}:
        return (
            "Queued deep review for ADVoi voice validation. You'll get a desktop brief link.",
            {"mode": "mock", "queued": True},
        )
    return (
        "Deep review queued for desktop prep. I'll surface the brief when it's ready.",
        {"queued": True},
    )


async def run_frame(frame_id: str, *, confirmed: bool = False) -> FrameResult:
    frame = get_frame(frame_id)
    if not frame:
        raise ValueError(f"Unknown frame: {frame_id}")

    agent = AGENTS.get(frame.agent_id)
    if not agent:
        raise ValueError(f"Unknown agent for frame: {frame_id}")

    if frame.id == "fleet_status":
        spoken, detail = await _run_fleet_scout()
        status = "ok"
    elif frame.id == "open_briefs":
        spoken, detail = await _run_brief_curator()
        status = "ok"
    elif frame.id == "queue_deep_review":
        spoken, detail = await _run_review_queue(confirmed=confirmed)
        status = "confirmation_required" if detail.get("awaiting_confirmation") else "ok"
    else:
        spoken, detail = "That frame is not wired yet.", {}
        status = "unsupported"

    preamble = agent.speaks_first
    full_spoken = f"{preamble} {spoken}".strip()

    return FrameResult(
        frame_id=frame.id,
        agent_id=agent.id,
        status=status,
        spoken_summary=full_spoken,
        detail=detail,
    )


def frame_to_dict(frame: DecisionFrame) -> dict[str, Any]:
    agent = AGENTS[frame.agent_id]
    return {
        "id": frame.id,
        "label": frame.label,
        "agent_id": frame.agent_id,
        "agent_name": agent.name,
        "requires_confirmation": frame.requires_confirmation,
        "voice_prompt": frame.voice_prompt,
    }