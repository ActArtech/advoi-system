"""Ephemeral memory — Redis rolling window only."""

from __future__ import annotations

import json
import os
from typing import Any

# Defaults (documented in docs/MEMORY-STACK.md). Override via env.
DEFAULT_EPHEMERAL_TTL_SEC = 3600
DEFAULT_MAX_TURNS = 5

# Backward-compatible module constants (defaults only — prefer getters at call sites).
EPHEMERAL_TTL_SEC = DEFAULT_EPHEMERAL_TTL_SEC
MAX_TURNS = DEFAULT_MAX_TURNS


def _parse_positive_int(raw: str | None, default: int, *, name: str) -> int:
    """Parse a positive integer env value; fall back to default on missing/invalid."""
    if raw is None or str(raw).strip() == "":
        return default
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return default
    if value < 1:
        return default
    return value


def ephemeral_ttl_sec() -> int:
    """Redis key TTL for voice-turn windows (seconds).

    Env: ``ADVOI_REDIS_VOICE_TTL_SEC`` (default ``3600``).
    """
    return _parse_positive_int(
        os.getenv("ADVOI_REDIS_VOICE_TTL_SEC"),
        DEFAULT_EPHEMERAL_TTL_SEC,
        name="ADVOI_REDIS_VOICE_TTL_SEC",
    )


def ephemeral_max_turns() -> int:
    """Max retained turns per session list (LTRIM window).

    Env: ``ADVOI_REDIS_VOICE_MAX_TURNS`` (default ``5``).
    """
    return _parse_positive_int(
        os.getenv("ADVOI_REDIS_VOICE_MAX_TURNS"),
        DEFAULT_MAX_TURNS,
        name="ADVOI_REDIS_VOICE_MAX_TURNS",
    )


def _redis_url() -> str:
    return os.getenv("REDIS_URL", "redis://redis:6379/0")


async def recall_ephemeral(session_id: str) -> list[dict[str, Any]]:
    try:
        import redis.asyncio as aioredis

        max_turns = ephemeral_max_turns()
        client = aioredis.from_url(_redis_url(), decode_responses=True)
        key = f"advoi:ephemeral:{session_id}"
        raw = await client.lrange(key, 0, max_turns - 1)
        await client.aclose()
        return [json.loads(x) for x in raw if x]
    except Exception:
        return []


async def retain_ephemeral(session_id: str, payload: dict[str, Any]) -> bool:
    try:
        import redis.asyncio as aioredis

        max_turns = ephemeral_max_turns()
        ttl = ephemeral_ttl_sec()
        client = aioredis.from_url(_redis_url(), decode_responses=True)
        key = f"advoi:ephemeral:{session_id}"
        await client.lpush(key, json.dumps(payload))
        await client.ltrim(key, 0, max_turns - 1)
        await client.expire(key, ttl)
        await client.aclose()
        return True
    except Exception:
        return False
