"""Agent result cache — fast bulk reads for API and PWA."""

from __future__ import annotations

import json
from typing import Any

from advoi.cache.redis_client import get_redis
from advoi.routing.agent_config import AGENT_FRAMES, INTERVAL_SECS
from advoi.routing.agents import AGENTS

CACHEABLE_STATUSES = frozenset({"ok", "confirmation_required"})


def cache_key(agent_id: str) -> str:
    return f"advoi:agent:{agent_id}:last"


def write_agent_cache(agent_id: str, payload: dict[str, Any]) -> bool:
    if payload.get("status") not in CACHEABLE_STATUSES:
        return False
    client = get_redis()
    if not client:
        return False
    try:
        client.setex(cache_key(agent_id), INTERVAL_SECS * 2, json.dumps(payload))
        return True
    except Exception:
        return False


def read_agent_cache(agent_id: str) -> dict[str, Any] | None:
    client = get_redis()
    if not client:
        return None
    try:
        raw = client.get(cache_key(agent_id))
        if not raw:
            return None
        return json.loads(raw)
    except Exception:
        return None


def read_all_agent_caches() -> dict[str, dict[str, Any]]:
    client = get_redis()
    if not client:
        return {}
    keys = [cache_key(aid) for aid in AGENT_FRAMES]
    try:
        values = client.mget(keys)
    except Exception:
        return {}
    out: dict[str, dict[str, Any]] = {}
    for agent_id, raw in zip(AGENT_FRAMES.keys(), values, strict=True):
        if not raw:
            continue
        try:
            out[agent_id] = json.loads(raw)
        except json.JSONDecodeError:
            continue
    return out


def agents_status_summary() -> dict[str, Any]:
    caches = read_all_agent_caches()
    agents: list[dict[str, Any]] = []
    ready = 0
    for a in AGENTS.values():
        row: dict[str, Any] = {
            "id": a.id,
            "name": a.name,
            "role": a.role,
            "speaks_first": a.speaks_first,
            "frame_id": AGENT_FRAMES.get(a.id),
            "cached": a.id in caches,
        }
        if a.id in caches:
            row["last_run"] = caches[a.id]
            ready += 1
        agents.append(row)
    total = len(AGENTS)
    return {
        "agents": agents,
        "ready": ready,
        "total": total,
        "all_ready": ready == total,
        "redis": get_redis() is not None,
    }