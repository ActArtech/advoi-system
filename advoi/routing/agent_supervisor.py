"""Run all specialist agents in one process (local testing)."""

from __future__ import annotations

import asyncio
import logging
import os
import sys

from advoi.routing.agent_bootstrap import prewarm_all_agents
from advoi.routing.agent_daemon import run_specialist
from advoi.routing.agents import AGENTS

logger = logging.getLogger("advoi.supervisor")

DEFAULT_AGENT_IDS = tuple(AGENTS.keys())


async def run_all(agent_ids: tuple[str, ...] = DEFAULT_AGENT_IDS) -> None:
    interval = os.getenv("ADVOI_AGENT_INTERVAL_SECS", "45")
    logger.info(
        "Supervisor starting %s agents (interval %ss): %s",
        len(agent_ids),
        interval,
        ", ".join(agent_ids),
    )
    await prewarm_all_agents()
    tasks = [asyncio.create_task(run_specialist(agent_id)) for agent_id in agent_ids]
    await asyncio.gather(*tasks)


def main() -> None:
    logging.basicConfig(level=os.getenv("ADVOI_LOG_LEVEL", "INFO"))
    ids = tuple(sys.argv[1:]) if len(sys.argv) > 1 else DEFAULT_AGENT_IDS
    unknown = [aid for aid in ids if aid not in AGENTS]
    if unknown:
        raise SystemExit(f"Unknown agent ids: {', '.join(unknown)}")
    try:
        asyncio.run(run_all(ids))
    except KeyboardInterrupt:
        logger.info("Supervisor stopped")


if __name__ == "__main__":
    main()