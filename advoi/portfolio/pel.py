"""Portfolio Event Log — append-only portfolio_events table in Postgres."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

_LOGGER = logging.getLogger(__name__)

_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS portfolio_events (
    id BIGSERIAL PRIMARY KEY,
    event_type TEXT NOT NULL,
    venture_slug TEXT,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
)
"""


async def ensure_portfolio_events_table() -> bool:
    """Create portfolio_events if missing. Returns False when DATABASE_URL unset."""
    dsn = os.getenv("DATABASE_URL", "")
    if not dsn:
        return False
    try:
        import psycopg

        async with await psycopg.AsyncConnection.connect(dsn) as conn:
            async with conn.cursor() as cur:
                await cur.execute(_TABLE_DDL)
            await conn.commit()
        return True
    except Exception as exc:
        _LOGGER.debug("portfolio_events ensure deferred: %s", exc)
        return False


async def _gate_snapshot_exists(cur, timestamp: str) -> bool:
    await cur.execute(
        """
        SELECT 1 FROM portfolio_events
        WHERE event_type = 'gate_snapshot'
          AND payload->>'timestamp' = %s
        LIMIT 1
        """,
        (timestamp,),
    )
    row = await cur.fetchone()
    return row is not None


async def append_portfolio_event(
    event_type: str,
    payload: dict[str, Any],
    venture_slug: str | None = None,
    *,
    dedupe_by_timestamp: bool = True,
) -> bool:
    """Append one portfolio event. Returns False when DATABASE_URL unset or on error."""
    dsn = os.getenv("DATABASE_URL", "")
    if not dsn:
        return False
    event_type = (event_type or "").strip()
    if not event_type:
        return False
    try:
        import psycopg

        async with await psycopg.AsyncConnection.connect(dsn) as conn:
            async with conn.cursor() as cur:
                await cur.execute(_TABLE_DDL)
                if (
                    dedupe_by_timestamp
                    and event_type == "gate_snapshot"
                    and (ts := str(payload.get("timestamp") or "").strip())
                ):
                    if await _gate_snapshot_exists(cur, ts):
                        return True
                await cur.execute(
                    """
                    INSERT INTO portfolio_events (event_type, venture_slug, payload)
                    VALUES (%s, %s, %s::jsonb)
                    """,
                    (event_type, venture_slug, json.dumps(payload)),
                )
            await conn.commit()
        return True
    except Exception as exc:
        _LOGGER.debug("portfolio_events append deferred: %s", exc)
        return False