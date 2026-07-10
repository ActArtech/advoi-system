"""Structured canonical state — Postgres only (not long-term recall synthesis)."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

_LOGGER = logging.getLogger(__name__)


async def retain_structured(event_type: str, payload: dict[str, Any]) -> bool:
    dsn = os.getenv("DATABASE_URL", "")
    if not dsn:
        return False
    try:
        import psycopg

        async with await psycopg.AsyncConnection.connect(dsn) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS memory_events (
                        id BIGSERIAL PRIMARY KEY,
                        event_type TEXT NOT NULL,
                        payload JSONB NOT NULL,
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    )
                    """
                )
                await cur.execute(
                    "INSERT INTO memory_events (event_type, payload) VALUES (%s, %s::jsonb)",
                    (event_type, json.dumps(payload)),
                )
            await conn.commit()
        return True
    except Exception as exc:
        _LOGGER.debug("postgres retain deferred: %s", exc)
        return False


async def _ensure_briefs_table(cur) -> None:
    await cur.execute(
        """
        CREATE TABLE IF NOT EXISTS decision_briefs (
            id BIGSERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            project TEXT DEFAULT 'advoi',
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
        """
    )


async def list_open_briefs(*, limit: int = 10) -> list[str] | None:
    """Return open brief titles, or None when Postgres is unavailable.

    Empty list means Postgres answered and there are no open briefs (canonical empty).
    None means DSN missing or query failed — callers may fall back to Redis cache.
    """
    dsn = os.getenv("DATABASE_URL", "")
    if not dsn:
        return None
    try:
        import psycopg

        async with await psycopg.AsyncConnection.connect(dsn) as conn:
            async with conn.cursor() as cur:
                await _ensure_briefs_table(cur)
                await cur.execute(
                    """
                    SELECT title FROM decision_briefs
                    WHERE status = 'open'
                    ORDER BY updated_at DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
                rows = await cur.fetchall()
        return [str(row[0]) for row in rows if row and row[0]]
    except Exception as exc:
        _LOGGER.debug("postgres briefs list deferred: %s", exc)
        return None


async def upsert_open_brief(title: str, *, project: str = "advoi") -> bool:
    """Insert an open brief into Postgres and invalidate Redis cache (ADR-026)."""
    dsn = os.getenv("DATABASE_URL", "")
    title = (title or "").strip()
    if not dsn or not title:
        return False
    try:
        import psycopg

        async with await psycopg.AsyncConnection.connect(dsn) as conn:
            async with conn.cursor() as cur:
                await _ensure_briefs_table(cur)
                await cur.execute(
                    """
                    INSERT INTO decision_briefs (title, status, project)
                    VALUES (%s, 'open', %s)
                    """,
                    (title, project),
                )
            await conn.commit()
        # Redis is cache-only: drop stale advoi:briefs:open after every PG write.
        from advoi.memory.briefs_cache import invalidate_open_briefs_cache

        invalidate_open_briefs_cache()
        return True
    except Exception as exc:
        _LOGGER.debug("postgres brief upsert deferred: %s", exc)
        return False