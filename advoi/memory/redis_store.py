"""Ephemeral memory — Redis rolling window only."""

from __future__ import annotations

import json
import os
from typing import Any

EPHEMERAL_TTL_SEC = 3600
MAX_TURNS = 5


def _redis_url() -> str:
    return os.getenv("REDIS_URL", "redis://redis:6379/0")


async def recall_ephemeral(session_id: str) -> list[dict[str, Any]]:
    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(_redis_url(), decode_responses=True)
        key = f"advoi:ephemeral:{session_id}"
        raw = await client.lrange(key, 0, MAX_TURNS - 1)
        await client.aclose()
        return [json.loads(x) for x in raw if x]
    except Exception:
        return []


async def retain_ephemeral(session_id: str, payload: dict[str, Any]) -> bool:
    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(_redis_url(), decode_responses=True)
        key = f"advoi:ephemeral:{session_id}"
        await client.lpush(key, json.dumps(payload))
        await client.ltrim(key, 0, MAX_TURNS - 1)
        await client.expire(key, EPHEMERAL_TTL_SEC)
        await client.aclose()
        return True
    except Exception:
        return False