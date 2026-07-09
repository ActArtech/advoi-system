"""Squad dispatch — bridge confirmed intents to FirstMate / Hermes crews."""

from __future__ import annotations

import logging
import os
import time
import uuid
from typing import Any

from advoi.squads.registry import SQUADS_BY_ID, Squad

_LOGGER = logging.getLogger(__name__)


async def dispatch_squad_job(
    squad_id: str,
    *,
    action: str,
    payload: dict[str, Any] | None = None,
    confirmed: bool = True,
) -> dict[str, Any]:
    squad = SQUADS_BY_ID.get(squad_id)
    if not squad:
        return {"ok": False, "error": f"Unknown squad: {squad_id}"}

    if squad.dispatch_target == "queue_deep_review" and not confirmed:
        return {
            "ok": False,
            "status": "confirmation_required",
            "squad_id": squad_id,
            "message": "Deep review dispatch requires confirmation.",
        }

    job_id = f"{squad_id}-{uuid.uuid4().hex[:8]}"
    job = {
        "job_id": job_id,
        "squad_id": squad_id,
        "squad_name": squad.name,
        "channel": squad.channel,
        "venture_id": squad.venture_id,
        "action": action,
        "status": "queued",
        "timestamp": time.time(),
        "payload": payload or {},
        "webhook_configured": bool(os.getenv("DISCORD_WEBHOOK_URL")),
    }

    try:
        from advoi.memory.router import MemoryRouter
        from advoi.memory.write_targets import MemoryEventType

        await MemoryRouter().retain(
            MemoryEventType.SQUAD_LESSON,
            {
                "summary": f"Squad dispatch {squad_id}: {action}",
                "job_id": job_id,
                "squad_id": squad_id,
                "venture_id": squad.venture_id,
            },
        )
    except Exception as exc:
        _LOGGER.debug("squad dispatch retain skipped: %s", exc)

    if os.getenv("ADVOI_SQUAD_MOCK", "true").lower() in {"1", "true", "yes"}:
        job["status"] = "mock_queued"
        job["ok"] = True
        return job

    webhook = os.getenv("DISCORD_WEBHOOK_URL", "")
    if webhook:
        try:
            import httpx

            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    webhook,
                    json={"content": f"[{squad.name}] {action} (job {job_id})"},
                )
            job["status"] = "dispatched"
        except Exception as exc:
            job["status"] = "webhook_failed"
            job["error"] = str(exc)
            job["ok"] = False
            return job

    job["ok"] = True
    return job


def squad_for_frame(frame_id: str) -> Squad | None:
    for squad in SQUADS_BY_ID.values():
        if squad.dispatch_target == frame_id:
            return squad
    return None