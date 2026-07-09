"""Two-phase Guardian notifications: issue detected then resolved."""

from __future__ import annotations

import logging
from typing import Any

from advoi.memory.guardian_log import append_guardian_event

_LOGGER = logging.getLogger(__name__)

# agent_id -> open issue id (in-process; persisted via guardian log)
_OPEN_ISSUES: dict[str, str] = {}


async def notify_issue_detected(
    agent_id: str,
    *,
    error: str,
    recovery_hint: str,
    context: dict[str, Any] | None = None,
) -> str:
    issue_id = f"{agent_id}-{len(_OPEN_ISSUES)}"
    _OPEN_ISSUES[agent_id] = issue_id
    payload = {
        "issue_id": issue_id,
        "agent_id": agent_id,
        "phase": "detected",
        "error": error,
        "recovery_hint": recovery_hint,
        "context": context or {},
    }
    await append_guardian_event("issue_detected", payload)
    _LOGGER.info("guardian detected issue %s for %s", issue_id, agent_id)
    return issue_id


async def notify_issue_resolved(
    agent_id: str,
    *,
    note: str = "tick recovered",
) -> bool:
    issue_id = _OPEN_ISSUES.pop(agent_id, None)
    if not issue_id:
        return False
    await append_guardian_event(
        "issue_resolved",
        {"issue_id": issue_id, "agent_id": agent_id, "phase": "resolved", "note": note},
    )
    _LOGGER.info("guardian resolved issue %s for %s", issue_id, agent_id)
    return True