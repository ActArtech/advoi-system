"""Singleton Redis client — reuse connections across agents and API."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import redis

_client: redis.Redis | None = None
_checked = False
_available = False


def get_redis() -> redis.Redis | None:
    global _client, _checked, _available
    if _checked:
        return _client
    _checked = True
    try:
        import redis as redis_lib

        url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        _client = redis_lib.from_url(url, decode_responses=True)
        _client.ping()
        _available = True
    except Exception:
        _client = None
        _available = False
    return _client


def redis_available() -> bool:
    get_redis()
    return _available