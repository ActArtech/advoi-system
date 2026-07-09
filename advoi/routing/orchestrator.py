"""Parallel multi-agent orchestration across decision frames and subsystems."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from advoi.cache.agent_cache import agents_status_summary
from advoi.copy_style import plain_copy
from advoi.decision.frames import FRAMES, FrameId, get_frame
from advoi.routing.agents import AGENTS

if TYPE_CHECKING:
    from advoi.routing.frame_runner import FrameResult

ALL_SPECIALIST_FRAME_IDS: tuple[FrameId, ...] = tuple(f.id for f in FRAMES)


@dataclass
class OrchestrateBundle:
    results: list[FrameResult]
    agents_used: list[str]
    systems: list[str]
    spoken_summary: str

SYSTEMS_BY_FRAME: dict[str, list[str]] = {
    "fleet_status": ["firstmate", "hermes", "aether"],
    "open_briefs": ["memory", "postgres", "redis"],
    "queue_deep_review": ["memory", "review-queue"],
    "systems_pulse": ["api", "firstmate", "memory", "redis"],
    "memory_health": ["memory", "hindsight", "redis", "postgres"],
    "latency_check": ["api", "observability"],
    "guardian_status": ["guardian", "api"],
    "deploy_readiness": ["api", "redis", "livekit", "staging"],
}


def systems_for_frame(frame_id: str) -> list[str]:
    return list(SYSTEMS_BY_FRAME.get(frame_id, []))


async def run_frames_parallel(
    frame_ids: list[FrameId],
    *,
    confirmed: bool = False,
    refresh: bool = False,
) -> list[FrameResult]:
    """Execute multiple frames concurrently; unknown ids are skipped."""
    from advoi.routing.frame_runner import run_frame

    valid = [fid for fid in frame_ids if get_frame(fid)]
    if not valid:
        return []
    return list(
        await asyncio.gather(
            *[
                run_frame(fid, confirmed=confirmed, refresh=refresh)
                for fid in valid
            ]
        )
    )


def _strip_agent_preamble(spoken: str, agent_id: str) -> str:
    agent = AGENTS.get(agent_id)
    if not agent:
        return spoken
    prefix = agent.speaks_first.strip()
    text = spoken.strip()
    if text.lower().startswith(prefix.lower()):
        return text[len(prefix) :].strip()
    return text


def synthesize_systems_pulse(
    fleet: "FrameResult",
    briefs: "FrameResult",
    *,
    agent_summary: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Merge specialist outputs into one spoken systems pulse."""
    summary = agent_summary or agents_status_summary()
    ready = int(summary.get("ready") or 0)
    total = int(summary.get("total") or len(AGENTS))

    fleet_core = _strip_agent_preamble(fleet.spoken_summary, fleet.agent_id)
    briefs_core = _strip_agent_preamble(briefs.spoken_summary, briefs.agent_id)

    parts = [
        f"Systems pulse: {ready} of {total} specialist agents are warm.",
        fleet_core,
        briefs_core,
    ]
    spoken = plain_copy(" ".join(p for p in parts if p))

    detail: dict[str, Any] = {
        "orchestration": "parallel",
        "agents_used": [fleet.agent_id, briefs.agent_id, "systems-pulse"],
        "systems": systems_for_frame("systems_pulse"),
        "agents_ready": ready,
        "agents_total": total,
        "subsystems": {
            "fleet": {
                "frame_id": fleet.frame_id,
                "status": fleet.status,
                "detail": fleet.detail,
            },
            "briefs": {
                "frame_id": briefs.frame_id,
                "status": briefs.status,
                "detail": briefs.detail,
            },
        },
    }
    return spoken, detail


def synthesize_run_all_summary(results: list[FrameResult]) -> str:
    """Condensed spoken summary after a full six-frame parallel run."""
    by_id = {r.frame_id: r for r in results}
    summary = agents_status_summary()
    ready = int(summary.get("ready") or 0)
    total = int(summary.get("total") or len(AGENTS))

    parts = [f"Full systems check complete. {ready} of {total} specialist agents are warm."]

    fleet = by_id.get("fleet_status")
    briefs = by_id.get("open_briefs")
    if fleet and briefs:
        pulse_spoken, _ = synthesize_systems_pulse(fleet, briefs, agent_summary=summary)
        parts.append(pulse_spoken)

    pulse = by_id.get("systems_pulse")
    if pulse and pulse.status != "ok":
        parts.append("Systems pulse reported degraded status.")

    for frame_id in ("memory_health", "guardian_status", "queue_deep_review"):
        row = by_id.get(frame_id)
        if not row:
            continue
        core = _strip_agent_preamble(row.spoken_summary, row.agent_id)
        if core:
            parts.append(core)

    return plain_copy(" ".join(p for p in parts if p))


def _bundle_from_results(results: list[FrameResult]) -> OrchestrateBundle:
    agents_used: list[str] = []
    systems: set[str] = set()
    for result in results:
        agents_used.extend(result.detail.get("agents_used") or [result.agent_id])
        systems.update(systems_for_frame(result.frame_id))
    return OrchestrateBundle(
        results=results,
        agents_used=list(dict.fromkeys(agents_used)),
        systems=sorted(systems),
        spoken_summary=synthesize_run_all_summary(results),
    )


async def run_all_specialist_frames(
    *,
    confirmed: bool = True,
    refresh: bool = False,
) -> OrchestrateBundle:
    """Run all six specialist frames in parallel."""
    results = await run_frames_parallel(
        list(ALL_SPECIALIST_FRAME_IDS),
        confirmed=confirmed,
        refresh=refresh,
    )
    return _bundle_from_results(results)


async def run_systems_pulse(*, refresh: bool = False) -> "FrameResult":
    """Run fleet + brief curators in parallel and synthesize one voice reply."""
    from advoi.routing.frame_runner import FrameResult, run_frame

    fleet, briefs = await asyncio.gather(
        run_frame("fleet_status", refresh=refresh),
        run_frame("open_briefs", refresh=refresh),
    )
    spoken, detail = synthesize_systems_pulse(fleet, briefs)
    agent = AGENTS["systems-pulse"]
    full_spoken = plain_copy(f"{agent.speaks_first} {spoken}".strip())
    status = "ok" if fleet.status == "ok" and briefs.status == "ok" else "degraded"
    return FrameResult(
        frame_id="systems_pulse",
        agent_id=agent.id,
        status=status,
        spoken_summary=full_spoken,
        detail=detail,
    )