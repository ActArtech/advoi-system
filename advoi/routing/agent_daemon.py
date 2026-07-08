"""Always-on specialist agents — cache frame results for voice/PWA."""

from __future__ import annotations

import asyncio
import logging
import os
import sys

logger = logging.getLogger("advoi.agent")

from advoi.routing.agent_bootstrap import tick_agent
from advoi.routing.agent_config import AGENT_FRAMES, INTERVAL_SECS, TICK_STAGGER_SECS
from advoi.routing.agents import AGENTS


async def run_specialist(agent_id: str) -> None:
    frame_id = AGENT_FRAMES.get(agent_id)
    if not frame_id:
        raise SystemExit(f"Unknown agent: {agent_id}")

    agent = AGENTS[agent_id]
    stagger = TICK_STAGGER_SECS.get(agent_id, 0)
    logger.info(
        "%s (%s) online, interval %ss, stagger %ss",
        agent.name,
        agent_id,
        INTERVAL_SECS,
        stagger,
    )
    if stagger > 0:
        await asyncio.sleep(stagger)

    while True:
        try:
            refresh = agent_id == "fleet-scout"
            payload = await tick_agent(agent_id, refresh=refresh)
            status = payload.get("status", "unknown") if payload else "empty"
            logger.info("%s tick ok: %s", agent_id, status)
        except Exception as exc:
            logger.error("%s tick failed: %s", agent_id, exc)
        await asyncio.sleep(INTERVAL_SECS)


def main() -> None:
    logging.basicConfig(level=os.getenv("ADVOI_LOG_LEVEL", "INFO"))
    if len(sys.argv) < 2:
        raise SystemExit("usage: python -m advoi.routing.agent_daemon <agent-id>")
    agent_id = sys.argv[1]
    asyncio.run(run_specialist(agent_id))


if __name__ == "__main__":
    main()