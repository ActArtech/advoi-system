"""Portfolio Event Log (PEL) — append-only control-plane events (moat R1).

See docs/architecture/07-portfolio-event-log.md.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import uuid
from datetime import UTC, datetime
from enum import Enum, StrEnum
from typing import Any

_LOGGER = logging.getLogger(__name__)

# In-memory rows when ADVOI_PEL_MEMORY=true (T0 tests / local without Postgres).
_MEMORY_ROWS: list[dict[str, Any]] = []

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS portfolio_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    venture_id      TEXT NOT NULL,
    source          TEXT NOT NULL,
    type            TEXT NOT NULL,
    payload         JSONB NOT NULL DEFAULT '{}'::jsonb,
    guardian_status TEXT NULL,
    execution_ref   TEXT NULL,
    trace_id        TEXT NULL,
    legacy_memory_event_id BIGINT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT portfolio_events_legacy_memory_event_id_key
        UNIQUE (legacy_memory_event_id)
)
"""

_CREATE_INDEXES_SQL = (
    """
    CREATE INDEX IF NOT EXISTS portfolio_events_venture_ts_idx
        ON portfolio_events (venture_id, timestamp DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS portfolio_events_source_type_ts_idx
        ON portfolio_events (source, type, timestamp DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS portfolio_events_trace_id_idx
        ON portfolio_events (trace_id)
        WHERE trace_id IS NOT NULL
    """,
    """
    CREATE INDEX IF NOT EXISTS portfolio_events_execution_ref_idx
        ON portfolio_events (execution_ref)
        WHERE execution_ref IS NOT NULL
    """,
)


class EventSource(StrEnum):
    """Controlled vocabulary for portfolio_events.source."""

    VOICE = "voice"
    INGEST = "ingest"
    FLEET = "fleet"
    PAPERCLIP = "paperclip"
    AETHER = "aether"
    API = "api"
    DAEMON = "daemon"
    SQUAD = "squad"
    GUARDIAN = "guardian"
    MEMORY = "memory"
    SYSTEM = "system"


class EventType(StrEnum):
    """Concrete portfolio_events.type values used by emit points."""

    FRAME_RUN = "frame_run"
    VOICE_INTENT = "voice_intent"
    SYSTEMS_PULSE = "systems_pulse"
    GOVERNANCE_DECISION = "governance_decision"
    DECISION_BRIEF = "decision_brief"
    REVIEW_QUEUED = "review_queued"
    FLEET_TRIGGER = "fleet_trigger"
    SQUAD_DISPATCH = "squad_dispatch"
    INGEST_DISPATCHED = "ingest_dispatched"
    PORTFOLIO_FACT = "portfolio_fact"
    SQUAD_LESSON = "squad_lesson"
    PROJECT_STATE = "project_state"
    MASTER_STATE = "master_state"
    GUARDIAN_GATE = "guardian_gate"
    CONFIRMATION_REQUIRED = "confirmation_required"
    CONFIRMATION_RESOLVED = "confirmation_resolved"
    # PWA thin beacon → POST /api/events (no third-party analytics SDK)
    PWA_CONNECT = "pwa_connect"
    FRAME_TAP = "frame_tap"
    CONFIRM_SHOWN = "confirm_shown"
    CONFIRM_ACCEPT = "confirm_accept"
    ERROR = "error"


# Allowed types for the PWA thin-beacon HTTP path (subset of EventType).
PWA_BEACON_EVENT_TYPES: frozenset[str] = frozenset(
    {
        EventType.PWA_CONNECT.value,
        EventType.FRAME_TAP.value,
        EventType.CONFIRM_SHOWN.value,
        EventType.CONFIRM_ACCEPT.value,
        EventType.ERROR.value,
    }
)


class GuardianStatus(StrEnum):
    """Gate outcome when applicable."""

    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    ALLOWED = "allowed"
    DENIED = "denied"
    ERROR = "error"


def reset_memory_store() -> None:
    """Clear in-memory PEL rows (tests only)."""
    _MEMORY_ROWS.clear()


def memory_rows() -> list[dict[str, Any]]:
    """Copy of in-memory PEL rows (tests only)."""
    return list(_MEMORY_ROWS)


def _pel_memory_enabled() -> bool:
    return os.getenv("ADVOI_PEL_MEMORY", "").lower() in {"1", "true", "yes"}


def _normalize_enum(value: EventSource | EventType | GuardianStatus | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)


def current_trace_id() -> str | None:
    """Best-effort OTel / request correlation id; None when unavailable.

    Re-exported from observability so PEL callers need not import otel_setup.
    """
    from advoi.observability.otel_setup import current_trace_id as _current_trace_id

    return _current_trace_id()


def transcript_hash(text: str, *, length: int = 16) -> str:
    """Short stable hash for voice payloads (avoid full transcript PII dump)."""
    digest = hashlib.sha256((text or "").encode("utf-8")).hexdigest()
    return digest[:length]


def _row_dict(
    *,
    event_id: str,
    timestamp: datetime,
    venture_id: str,
    source: str,
    event_type: str,
    payload: dict[str, Any],
    guardian_status: str | None,
    execution_ref: str | None,
    trace_id: str | None,
    legacy_memory_event_id: int | None,
    created_at: datetime,
) -> dict[str, Any]:
    return {
        "id": event_id,
        "timestamp": timestamp,
        "venture_id": venture_id,
        "source": source,
        "type": event_type,
        "payload": payload,
        "guardian_status": guardian_status,
        "execution_ref": execution_ref,
        "trace_id": trace_id,
        "legacy_memory_event_id": legacy_memory_event_id,
        "created_at": created_at,
    }


def _append_in_memory(row: dict[str, Any]) -> str | None:
    legacy = row.get("legacy_memory_event_id")
    if legacy is not None:
        for existing in _MEMORY_ROWS:
            if existing.get("legacy_memory_event_id") == legacy:
                # Idempotent: duplicate legacy key does not create a new row.
                return str(existing["id"])
    _MEMORY_ROWS.append(row)
    return str(row["id"])


async def ensure_portfolio_events_table(cur: Any | None = None) -> bool:
    """Create portfolio_events + indexes. Uses DATABASE_URL when cur is None."""
    if cur is not None:
        await cur.execute(_CREATE_TABLE_SQL)
        for stmt in _CREATE_INDEXES_SQL:
            await cur.execute(stmt)
        return True

    dsn = os.getenv("DATABASE_URL", "")
    if not dsn:
        return False
    try:
        import psycopg

        async with await psycopg.AsyncConnection.connect(dsn) as conn:
            async with conn.cursor() as db_cur:
                await ensure_portfolio_events_table(db_cur)
            await conn.commit()
        return True
    except Exception as exc:
        _LOGGER.debug("portfolio_events ensure deferred: %s", exc)
        return False


async def append_event(
    *,
    venture_id: str,
    source: EventSource | str,
    event_type: EventType | str,
    payload: dict[str, Any] | None = None,
    guardian_status: GuardianStatus | str | None = None,
    execution_ref: str | None = None,
    trace_id: str | None = None,
    timestamp: datetime | None = None,
    legacy_memory_event_id: int | None = None,
) -> str | None:
    """Append one PEL row. Returns event id string, or None when not persisted.

    Persistence:
    - Postgres when ``DATABASE_URL`` is set
    - In-memory when ``ADVOI_PEL_MEMORY=true`` (tests)
    - Otherwise no-op (returns None)

    Idempotency: when ``legacy_memory_event_id`` is set, duplicate keys do not
    create a second row (SQL UNIQUE + ON CONFLICT DO NOTHING; memory store match).
    """
    now = datetime.now(UTC)
    ts = timestamp or now
    source_s = _normalize_enum(source) or EventSource.SYSTEM.value
    type_s = _normalize_enum(event_type) or "unknown"
    status_s = _normalize_enum(guardian_status)
    body = dict(payload or {})
    tid = trace_id if trace_id is not None else current_trace_id()
    event_id = str(uuid.uuid4())
    venture = (venture_id or "unknown").strip() or "unknown"

    row = _row_dict(
        event_id=event_id,
        timestamp=ts,
        venture_id=venture,
        source=source_s,
        event_type=type_s,
        payload=body,
        guardian_status=status_s,
        execution_ref=execution_ref,
        trace_id=tid,
        legacy_memory_event_id=legacy_memory_event_id,
        created_at=now,
    )

    dsn = os.getenv("DATABASE_URL", "")
    if not dsn:
        if _pel_memory_enabled():
            return _append_in_memory(row)
        return None

    try:
        import psycopg

        async with await psycopg.AsyncConnection.connect(dsn) as conn:
            async with conn.cursor() as cur:
                await ensure_portfolio_events_table(cur)
                await cur.execute(
                    """
                    INSERT INTO portfolio_events (
                        id, timestamp, venture_id, source, type, payload,
                        guardian_status, execution_ref, trace_id,
                        legacy_memory_event_id, created_at
                    )
                    VALUES (
                        %s::uuid, %s, %s, %s, %s, %s::jsonb,
                        %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (legacy_memory_event_id) DO NOTHING
                    RETURNING id
                    """,
                    (
                        event_id,
                        ts,
                        venture,
                        source_s,
                        type_s,
                        json.dumps(body),
                        status_s,
                        execution_ref,
                        tid,
                        legacy_memory_event_id,
                        now,
                    ),
                )
                returned = await cur.fetchone()
            await conn.commit()
        if returned and returned[0]:
            return str(returned[0])
        # Conflict path: no new row; return existing id when legacy key set.
        if legacy_memory_event_id is not None:
            async with await psycopg.AsyncConnection.connect(dsn) as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        SELECT id FROM portfolio_events
                        WHERE legacy_memory_event_id = %s
                        """,
                        (legacy_memory_event_id,),
                    )
                    existing = await cur.fetchone()
                if existing and existing[0]:
                    return str(existing[0])
        return event_id if legacy_memory_event_id is None else None
    except Exception as exc:
        _LOGGER.debug("portfolio_events append deferred: %s", exc)
        if _pel_memory_enabled():
            return _append_in_memory(row)
        return None


async def safe_append_event(**kwargs: Any) -> str | None:
    """append_event that never raises (emit points use this)."""
    try:
        return await append_event(**kwargs)
    except Exception as exc:
        _LOGGER.debug("PEL append skipped: %s", exc)
        return None
