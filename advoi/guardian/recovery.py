"""Guardian recovery — log agent failures and surface recovery hints."""

from __future__ import annotations

import logging
from typing import Any

from advoi.memory.guardian_log import append_guardian_event

_LOGGER = logging.getLogger(__name__)

RECOVERY_HINTS: dict[str, str] = {
    "fleet-scout": "Check FIRSTMATE_FLEET_PATH and Hermes bridge; mock mode uses ADVOI_FRAME_MOCK=true.",
    "brief-curator": "Verify DATABASE_URL and seeded briefs; falls back to mock briefs when Postgres unavailable.",
    "review-queue": "Confirm Postgres review_queue table; mock mode queues to /briefs/0.",
    "systems-pulse": "Runs fleet + briefs in parallel; fix upstream agents first.",
    "memory-scout": "Check HINDSIGHT_BRIDGE_URL, REDIS_URL, DATABASE_URL, operational store path.",
    "guardian-sentinel": "Inspect docs/error-log/guardian-events.jsonl for recent failures.",
}


async def record_agent_failure(
    agent_id: str,
    error: BaseException | str,
    *,
    context: dict[str, Any] | None = None,
) -> bool:
    message = str(error)
    payload = {
        "agent_id": agent_id,
        "error": message,
        "recovery_hint": RECOVERY_HINTS.get(agent_id, "Check logs and retry tick."),
        "context": context or {},
    }
    _LOGGER.warning("guardian: agent %s failed: %s", agent_id, message)
    return await append_guardian_event("agent_tick_failed", payload)


async def record_recovery(agent_id: str, note: str) -> bool:
    return await append_guardian_event(
        "agent_recovered",
        {"agent_id": agent_id, "note": note},
    )