"""Structured canonical state — Postgres only (not long-term recall synthesis)."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

_LOGGER = logging.getLogger(__name__)

# Legacy memory_events age pruning (not PEL / portfolio_events).
# Safe default: keep 90 days; override via ADVOI_MEMORY_EVENTS_RETENTION_DAYS.
DEFAULT_MEMORY_EVENTS_RETENTION_DAYS = 90
MIN_MEMORY_EVENTS_RETENTION_DAYS = 7


def memory_events_retention_days() -> int:
    """Configured retention window for legacy ``memory_events`` rows.

    Env: ``ADVOI_MEMORY_EVENTS_RETENTION_DAYS`` (default ``90``, floor ``7``).
    """
    raw = os.getenv("ADVOI_MEMORY_EVENTS_RETENTION_DAYS")
    if raw is None or str(raw).strip() == "":
        return DEFAULT_MEMORY_EVENTS_RETENTION_DAYS
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return DEFAULT_MEMORY_EVENTS_RETENTION_DAYS
    if value < MIN_MEMORY_EVENTS_RETENTION_DAYS:
        return MIN_MEMORY_EVENTS_RETENTION_DAYS
    return value


def memory_events_retention_cutoff(
    *,
    now: datetime | None = None,
    retention_days: int | None = None,
) -> datetime:
    """UTC cutoff: rows with ``created_at`` strictly older than this are prunable.

    Pure helper for unit tests and the retention job. Does not touch the database.
    """
    days = retention_days if retention_days is not None else memory_events_retention_days()
    if days < 1:
        raise ValueError("retention_days must be >= 1")
    base = now if now is not None else datetime.now(timezone.utc)
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    else:
        base = base.astimezone(timezone.utc)
    return base - timedelta(days=days)


async def retain_structured(event_type: str, payload: dict[str, Any]) -> bool:
    """Insert a legacy memory_events row.

    Schema is owned by ``deploy/migrations/000_baseline_tables.sql`` (API boot).
    """
    dsn = os.getenv("DATABASE_URL", "")
    if not dsn:
        return False
    try:
        import psycopg

        async with await psycopg.AsyncConnection.connect(dsn) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO memory_events (event_type, payload) VALUES (%s, %s::jsonb)",
                    (event_type, json.dumps(payload)),
                )
            await conn.commit()
        return True
    except Exception as exc:
        _LOGGER.debug("postgres retain deferred: %s", exc)
        return False


async def prune_memory_events(
    *,
    retention_days: int | None = None,
    dry_run: bool = True,
    cutoff: datetime | None = None,
) -> dict[str, Any]:
    """Age-prune legacy ``memory_events`` older than the retention window.

    **Does not** touch ``portfolio_events`` (PEL), ``decision_briefs``, or
    ``review_queue``. Default is dry-run (count only).

    Returns a result dict:
      ``ok``, ``dry_run``, ``retention_days``, ``cutoff`` (ISO), ``matched``,
      ``deleted``, ``error`` (optional).
    """
    days = retention_days if retention_days is not None else memory_events_retention_days()
    if days < MIN_MEMORY_EVENTS_RETENTION_DAYS:
        days = MIN_MEMORY_EVENTS_RETENTION_DAYS
    cut = cutoff if cutoff is not None else memory_events_retention_cutoff(retention_days=days)
    if cut.tzinfo is None:
        cut = cut.replace(tzinfo=timezone.utc)

    result: dict[str, Any] = {
        "ok": False,
        "dry_run": dry_run,
        "retention_days": days,
        "cutoff": cut.isoformat(),
        "matched": 0,
        "deleted": 0,
    }

    dsn = os.getenv("DATABASE_URL", "")
    if not dsn:
        result["error"] = "DATABASE_URL not set"
        return result

    try:
        import psycopg

        async with await psycopg.AsyncConnection.connect(dsn) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT COUNT(*) FROM memory_events WHERE created_at < %s",
                    (cut,),
                )
                row = await cur.fetchone()
                matched = int(row[0]) if row and row[0] is not None else 0
                result["matched"] = matched

                if dry_run or matched == 0:
                    result["ok"] = True
                    result["deleted"] = 0
                    return result

                await cur.execute(
                    "DELETE FROM memory_events WHERE created_at < %s",
                    (cut,),
                )
                deleted = cur.rowcount if cur.rowcount is not None else matched
            await conn.commit()
        result["deleted"] = int(deleted)
        result["ok"] = True
        return result
    except Exception as exc:
        _LOGGER.warning("memory_events prune failed: %s", exc)
        result["error"] = str(exc)
        return result


async def list_open_briefs(*, limit: int = 10) -> list[str] | None:
    """Return open brief titles, or None when Postgres is unavailable.

    Empty list means Postgres answered and there are no open briefs (canonical empty).
    None means DSN missing or query failed — callers may fall back to Redis cache.

    Table: ``decision_briefs`` via ``deploy/migrations/000_baseline_tables.sql``.
    """
    dsn = os.getenv("DATABASE_URL", "")
    if not dsn:
        return None
    try:
        import psycopg

        async with await psycopg.AsyncConnection.connect(dsn) as conn:
            async with conn.cursor() as cur:
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
