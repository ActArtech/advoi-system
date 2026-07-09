"""Multi-agent run + squad dispatch orchestration."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from advoi.routing.orchestrator import OrchestrateBundle, run_all_specialist_frames
from advoi.squads.dispatch import dispatch_squad_job
from advoi.squads.registry import SQUADS, squad_for_agent

_LOGGER = logging.getLogger(__name__)


async def dispatch_all_squads(*, confirmed: bool = True) -> dict[str, Any]:
    """Queue jobs for every registered squad in parallel."""
    jobs = await asyncio.gather(
        *[
            dispatch_squad_job(
                squad.id,
                action=f"run_{squad.dispatch_target}",
                confirmed=confirmed,
            )
            for squad in SQUADS
        ]
    )
    ok = sum(1 for j in jobs if j.get("ok"))
    return {
        "ok": ok == len(SQUADS),
        "dispatched": ok,
        "total": len(SQUADS),
        "jobs": jobs,
    }


async def dispatch_squads_for_agents(agent_ids: list[str], *, confirmed: bool = True) -> list[dict[str, Any]]:
    """Dispatch one job per unique squad covering the given agent ids."""
    seen: set[str] = set()
    tasks: list[Any] = []
    for agent_id in agent_ids:
        squad = squad_for_agent(agent_id)
        if not squad or squad.id in seen:
            continue
        seen.add(squad.id)
        tasks.append(
            dispatch_squad_job(
                squad.id,
                action=f"agent_tick_{agent_id}",
                payload={"agent_id": agent_id},
                confirmed=confirmed,
            )
        )
    if not tasks:
        return []
    return list(await asyncio.gather(*tasks))


async def retain_orchestration_memory(bundle: OrchestrateBundle) -> None:
    """Persist multi-agent run summary to operational memory."""
    try:
        from advoi.memory.operational_bridge import retain_operational_unified

        await retain_operational_unified(
            "orchestration_run",
            {
                "summary": bundle.spoken_summary[:500],
                "agents_used": bundle.agents_used,
                "systems": bundle.systems,
                "frame_count": len(bundle.results),
                "statuses": {r.frame_id: r.status for r in bundle.results},
            },
        )
    except Exception as exc:
        _LOGGER.debug("orchestration retain skipped: %s", exc)


async def run_six_with_platform(
    *,
    confirmed: bool = True,
    refresh: bool = False,
    dispatch_squads: bool = False,
    retain_memory: bool = True,
) -> dict[str, Any]:
    """Run all six frames, optionally retain memory and dispatch squads."""
    bundle = await run_all_specialist_frames(confirmed=confirmed, refresh=refresh)
    if retain_memory:
        await retain_orchestration_memory(bundle)

    squad_jobs: list[dict[str, Any]] = []
    squad_summary: dict[str, Any] | None = None
    if dispatch_squads:
        squad_summary = await dispatch_all_squads(confirmed=confirmed)
        squad_jobs = squad_summary.get("jobs") or []

    return {
        "ok": True,
        "results": bundle.results,
        "agents_used": bundle.agents_used,
        "systems": bundle.systems,
        "spoken_summary": bundle.spoken_summary,
        "squads": squad_summary,
        "squad_jobs": squad_jobs,
    }