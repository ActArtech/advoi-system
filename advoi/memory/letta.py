"""Letta integration — optional operational/identity memory (ADR-026 v0.2)."""

from __future__ import annotations

import os
from typing import Any

from advoi.memory.letta_client import (
    LettaConfig,
    load_letta_config,
    probe_health,
    recall_passages,
    retain_passage,
)


def _cfg_for(base_url: str, agent_id: str) -> LettaConfig:
    base = load_letta_config()
    return LettaConfig(
        enabled=True,
        base_url=base_url.rstrip("/"),
        agent_id=agent_id,
        api_key=base.api_key,
    )


async def recall_operational(
    query: str,
    *,
    base_url: str,
    agent_id: str,
) -> list[dict[str, Any]]:
    if not base_url:
        return []
    return await recall_passages(query, cfg=_cfg_for(base_url, agent_id))


async def retain_operational(
    event_type: str,
    payload: dict[str, Any],
    *,
    base_url: str,
    agent_id: str,
) -> bool:
    if not base_url:
        return False
    return await retain_passage(event_type, payload, cfg=_cfg_for(base_url, agent_id))


__all__ = ["recall_operational", "retain_operational", "probe_health", "load_letta_config"]