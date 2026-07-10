"""Review queue — Postgres persistence for deep review desktop briefs."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any

_LOGGER = logging.getLogger(__name__)

DEFAULT_BRIEF_BASE_URL = "https://advoi.keyteller.com/briefs"


def desktop_brief_url(queue_id: int | str) -> str:
    base = os.getenv("ADVOI_DESKTOP_BRIEF_BASE_URL", DEFAULT_BRIEF_BASE_URL).rstrip("/")
    return f"{base}/{queue_id}"


async def ensure_table() -> bool:
    """Ensure review_queue via versioned migrations when DATABASE_URL is set.

    Schema lives in ``deploy/migrations/000_baseline_tables.sql``; API boot
    applies pending migrations. This is a best-effort ensure for non-API paths.
    """
    dsn = os.getenv("DATABASE_URL", "")
    if not dsn:
        return False
    try:
        from advoi.db.migrations import apply_pending_migrations

        result = await apply_pending_migrations()
        return result.ok and result.reason != "no_database_url"
    except Exception as exc:
        _LOGGER.debug("postgres review ensure_table deferred: %s", exc)
        return False


def _row_to_dict(row: tuple[Any, ...]) -> dict[str, Any]:
    queue_id, title, source_frame, status, metadata, created_at = row
    created = created_at.isoformat() if isinstance(created_at, datetime) else str(created_at)
    meta = metadata if isinstance(metadata, dict) else {}
    return {
        "queue_id": int(queue_id),
        "title": str(title),
        "source_frame": str(source_frame),
        "status": str(status),
        "metadata": meta,
        "brief_url": desktop_brief_url(int(queue_id)),
        "created_at": created,
    }


async def enqueue_review(
    title: str,
    source_frame: str,
    metadata: dict[str, Any] | None = None,
) -> int | None:
    dsn = os.getenv("DATABASE_URL", "")
    title = (title or "").strip()
    if not dsn or not title:
        return None
    try:
        import psycopg

        async with await psycopg.AsyncConnection.connect(dsn) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO review_queue (title, source_frame, status, metadata)
                    VALUES (%s, %s, 'pending', %s::jsonb)
                    RETURNING id
                    """,
                    (title, source_frame, json.dumps(metadata or {})),
                )
                row = await cur.fetchone()
            await conn.commit()
        if row and row[0] is not None:
            return int(row[0])
        return None
    except Exception as exc:
        _LOGGER.debug("postgres review enqueue deferred: %s", exc)
        return None


async def get_review_item(queue_id: int) -> dict[str, Any] | None:
    dsn = os.getenv("DATABASE_URL", "")
    if not dsn:
        return None
    try:
        import psycopg

        async with await psycopg.AsyncConnection.connect(dsn) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT id, title, source_frame, status, metadata, created_at
                    FROM review_queue
                    WHERE id = %s
                    LIMIT 1
                    """,
                    (queue_id,),
                )
                row = await cur.fetchone()
        return _row_to_dict(row) if row else None
    except Exception as exc:
        _LOGGER.debug("postgres review get deferred: %s", exc)
        return None


async def list_pending(*, limit: int = 20) -> list[dict[str, Any]]:
    dsn = os.getenv("DATABASE_URL", "")
    if not dsn:
        return []
    try:
        import psycopg

        async with await psycopg.AsyncConnection.connect(dsn) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT id, title, source_frame, status, metadata, created_at
                    FROM review_queue
                    WHERE status = 'pending'
                    ORDER BY created_at ASC
                    LIMIT %s
                    """,
                    (limit,),
                )
                rows = await cur.fetchall()
        return [_row_to_dict(row) for row in rows if row]
    except Exception as exc:
        _LOGGER.debug("postgres review list deferred: %s", exc)
        return []