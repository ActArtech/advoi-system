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