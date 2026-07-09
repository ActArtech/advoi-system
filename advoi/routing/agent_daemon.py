"""Always-on specialist agents — cache frame results for voice/PWA."""

from __future__ import annotations

import asyncio
import logging
import os
import sys

logger = logging.getLogger("advoi.agent")

_agent_had_failure: dict[str, bool] = {}

from advoi.routing.agent_bootstrap import tick_agent
from advoi.routing.agent_config import AGENT_FRAMES, INTERVAL_SECS, TICK_STAGGER_SECS
from advoi.routing.agent_control import agents_paused
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

    from advoi.guardian.auto_restart import run_with_auto_restart

    async def _on_tick_exhausted(exc: BaseException) -> None:
        logger.error("%s tick failed after auto-restart retries: %s", agent_id, exc)
        try:
            from advoi.guardian.notifications import notify_issue_detected
            from advoi.guardian.recovery import RECOVERY_HINTS, record_agent_failure

            await record_agent_failure(agent_id, exc)
            if not _agent_had_failure.get(agent_id):
                await notify_issue_detected(
                    agent_id,
                    error=str(exc),
                    recovery_hint=RECOVERY_HINTS.get(agent_id, "Check logs and retry."),
                )
                _agent_had_failure[agent_id] = True
        except Exception:
            pass

    while True:
        if agents_paused():
            await asyncio.sleep(min(INTERVAL_SECS, 15))
            continue
        try:
            refresh = agent_id == "fleet-scout"

            async def _tick() -> dict | None:
                return await tick_agent(agent_id, refresh=refresh)

            payload = await run_with_auto_restart(
                agent_id,
                _tick,
                on_exhausted=_on_tick_exhausted,
            )
            status = payload.get("status", "unknown") if payload else "empty"
            logger.info("%s tick ok: %s", agent_id, status)
            if _agent_had_failure.pop(agent_id, False):
                try:
                    from advoi.guardian.notifications import notify_issue_resolved
                    from advoi.guardian.recovery import record_recovery

                    await notify_issue_resolved(agent_id, note=f"tick ok: {status}")
                    await record_recovery(agent_id, f"auto-restart recovered: {status}")
                except Exception:
                    pass
        except Exception:
            pass
        await asyncio.sleep(INTERVAL_SECS)


def main() -> None:
    logging.basicConfig(level=os.getenv("ADVOI_LOG_LEVEL", "INFO"))
    if len(sys.argv) < 2:
        raise SystemExit("usage: python -m advoi.routing.agent_daemon <agent-id>")
    agent_id = sys.argv[1]
    asyncio.run(run_specialist(agent_id))


if __name__ == "__main__":
    main()