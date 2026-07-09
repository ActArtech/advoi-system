"""Parallel agent cache warm — fast first PWA/voice response."""

from __future__ import annotations

import asyncio
import logging
import time

from advoi.cache.agent_cache import write_agent_cache
from advoi.memory.write_targets import MemoryEventType
from advoi.routing.agent_config import AGENT_FRAMES
from advoi.routing.frame_runner import run_frame

logger = logging.getLogger("advoi.bootstrap")


def _agent_refresh_policy(agent_id: str) -> bool:
    """Live probes refresh on tick; curators warm from stores on first pass."""
    return agent_id in {
        "fleet-scout",
        "systems-pulse",
        "memory-scout",
        "guardian-sentinel",
    }


async def tick_agent(agent_id: str, *, refresh: bool | None = None) -> dict | None:
    frame_id = AGENT_FRAMES.get(agent_id)
    if not frame_id:
        return None
    use_refresh = _agent_refresh_policy(agent_id) if refresh is None else refresh
    confirmed = False
    result = await run_frame(frame_id, confirmed=confirmed, refresh=use_refresh)
    payload = {
        "agent_id": result.agent_id,
        "frame_id": result.frame_id,
        "status": result.status,
        "spoken_summary": result.spoken_summary,
        "timestamp": time.time(),
    }
    if not write_agent_cache(agent_id, payload):
        if result.status not in ("ok", "confirmation_required"):
            logger.debug("No cache for %s status=%s", agent_id, result.status)

    if result.status in ("ok", "confirmation_required"):
        try:
            from advoi.memory.router import MemoryRouter

            await MemoryRouter().retain(
                MemoryEventType.SQUAD_LESSON,
                {
                    "summary": result.spoken_summary[:500],
                    "agent_id": agent_id,
                    "frame_id": frame_id,
                    "status": result.status,
                },
            )
        except Exception as exc:
            logger.debug("operational retain skipped for %s: %s", agent_id, exc)

    return payload


async def prewarm_all_agents() -> list[dict]:
    """Run all specialists in parallel — sub-second when mock/cache hot."""
    agent_ids = tuple(AGENT_FRAMES.keys())
    logger.info("Prewarming %s agents in parallel", len(agent_ids))
    results = await asyncio.gather(
        *[tick_agent(aid, refresh=True) for aid in agent_ids],
        return_exceptions=True,
    )
    ok = sum(1 for r in results if isinstance(r, dict))
    logger.info("Prewarm complete: %s/%s agents cached", ok, len(agent_ids))
    return [r for r in results if isinstance(r, dict)]