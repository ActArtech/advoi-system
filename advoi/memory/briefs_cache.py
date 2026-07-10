"""Redis cache for open decision briefs — never a second source of truth.

ADR-026 / ship #2b:
  Postgres ``decision_briefs`` is canonical.
  Redis key ``advoi:briefs:open`` is a fill-on-read / invalidate-on-write cache only.
  Hindsight may enrich when Postgres is empty; it is not merged with PG/Redis titles.
"""

from __future__ import annotations

import json
import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)

OPEN_BRIEFS_KEY = "advoi:briefs:open"


def invalidate_open_briefs_cache() -> bool:
    """Delete the open-briefs Redis key after a Postgres write."""
    try:
        from advoi.cache.redis_client import get_redis

        client = get_redis()
        if not client:
            return False
        client.delete(OPEN_BRIEFS_KEY)
        return True
    except Exception as exc:
        _LOGGER.debug("briefs cache invalidate deferred: %s", exc)
        return False


def fill_open_briefs_cache(titles: list[str]) -> bool:
    """Write Postgres-canonical titles into Redis (replace, never merge)."""
    try:
        from advoi.cache.redis_client import get_redis

        client = get_redis()
        if not client:
            return False
        clean = [str(t)[:120] for t in titles if t and str(t).strip()]
        client.set(OPEN_BRIEFS_KEY, json.dumps(clean))
        return True
    except Exception as exc:
        _LOGGER.debug("briefs cache fill deferred: %s", exc)
        return False


def read_open_briefs_cache() -> list[str]:
    """Read Redis cache only (degraded fallback when Postgres is unavailable)."""
    try:
        from advoi.cache.redis_client import get_redis

        client = get_redis()
        if not client:
            return []
        raw = client.get(OPEN_BRIEFS_KEY)
        if not raw:
            return []
        data: Any = json.loads(raw)
        if isinstance(data, list):
            return [str(x)[:120] for x in data if x]
    except Exception as exc:
        _LOGGER.debug("briefs cache read deferred: %s", exc)
    return []
