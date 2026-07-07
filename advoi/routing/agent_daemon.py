"""Always-on specialist agents — cache frame results for voice/PWA."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys

logger = logging.getLogger("advoi.agent")

from advoi.routing.agents import AGENTS
from advoi.routing.frame_runner import run_frame

AGENT_FRAMES: dict[str, str] = {
    "fleet-scout": "fleet_status",
    "brief-curator": "open_briefs",
    "review-queue": "queue_deep_review",
}

INTERVAL_SECS = int(os.getenv("ADVOI_AGENT_INTERVAL_SECS", "180"))


async def _cache_result(agent_id: str, payload: dict) -> None:
    try:
        import redis

        url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        client = redis.from_url(url, decode_responses=True)
        client.setex(f"advoi:agent:{agent_id}:last", INTERVAL_SECS * 2, json.dumps(payload))
    except Exception as exc:
        logger.warning("Redis cache skip for {}: {}", agent_id, exc)


async def run_specialist(agent_id: str) -> None:
    frame_id = AGENT_FRAMES.get(agent_id)
    if not frame_id:
        raise SystemExit(f"Unknown agent: {agent_id}")

    agent = AGENTS[agent_id]
    logger.info("{} ({}) online — interval {}s", agent.name, agent_id, INTERVAL_SECS)

    while True:
        try:
            confirmed = frame_id == "queue_deep_review"
            result = await run_frame(frame_id, confirmed=confirmed)
            payload = {
                "agent_id": result.agent_id,
                "frame_id": result.frame_id,
                "status": result.status,
                "spoken_summary": result.spoken_summary,
            }
            await _cache_result(agent_id, payload)
            logger.info("{} tick ok: {}", agent_id, result.status)
        except Exception as exc:
            logger.error("{} tick failed: {}", agent_id, exc)
        await asyncio.sleep(INTERVAL_SECS)


def main() -> None:
    logging.basicConfig(level=os.getenv("ADVOI_LOG_LEVEL", "INFO"))
    if len(sys.argv) < 2:
        raise SystemExit("usage: python -m advoi.routing.agent_daemon <agent-id>")
    agent_id = sys.argv[1]
    asyncio.run(run_specialist(agent_id))


if __name__ == "__main__":
    main()