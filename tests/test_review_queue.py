"""Review queue Postgres persistence, CRUD round-trip, and API tests (T0)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from advoi.memory import review_queue
from advoi.routing.frame_runner import run_frame

# ---------------------------------------------------------------------------
# URL helpers / no-DB guards
# ---------------------------------------------------------------------------


def test_desktop_brief_url_default(monkeypatch):
    monkeypatch.delenv("ADVOI_DESKTOP_BRIEF_BASE_URL", raising=False)
    assert review_queue.desktop_brief_url(42) == "https://advoi.keyteller.com/briefs/42"


def test_desktop_brief_url_custom_base(monkeypatch):
    monkeypatch.setenv("ADVOI_DESKTOP_BRIEF_BASE_URL", "https://example.com/briefs/")
    assert review_queue.desktop_brief_url(7) == "https://example.com/briefs/7"


@pytest.mark.asyncio
async def test_enqueue_review_without_database(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert await review_queue.enqueue_review("Test", "queue_deep_review") is None


@pytest.mark.asyncio
async def test_list_pending_without_database(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert await review_queue.list_pending() == []


@pytest.mark.asyncio
async def test_dequeue_without_database(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert await review_queue.dequeue_review(1) is None


@pytest.mark.asyncio
async def test_ensure_table_without_database(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert await review_queue.ensure_table() is False


# ---------------------------------------------------------------------------
# Lightweight AsyncConnection mocks (single-call unit tests)
# ---------------------------------------------------------------------------


class _AsyncContext:
    def __init__(self, value):
        self._value = value

    async def __aenter__(self):
        return self._value

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeConn:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return _AsyncContext(self._cursor)

    async def commit(self):
        return None


def _mock_postgres_cursor(*, fetchone=None, fetchall=None):
    mock_cur = AsyncMock()
    if fetchone is not None:
        mock_cur.fetchone = AsyncMock(return_value=fetchone)
    if fetchall is not None:
        mock_cur.fetchall = AsyncMock(return_value=fetchall)

    mock_conn = _FakeConn(mock_cur)

    async def fake_connect(_dsn):
        return _AsyncContext(mock_conn)

    return fake_connect, mock_cur


@pytest.mark.asyncio
async def test_enqueue_review_persists(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test")

    fake_connect, mock_cur = _mock_postgres_cursor(fetchone=(99,))

    with patch("psycopg.AsyncConnection.connect", side_effect=fake_connect):
        queue_id = await review_queue.enqueue_review(
            "ADVoi voice launch",
            "queue_deep_review",
            metadata={"trigger": "test"},
        )

    assert queue_id == 99
    mock_cur.execute.assert_any_call(
        """
                    INSERT INTO review_queue (title, source_frame, status, metadata)
                    VALUES (%s, %s, %s, %s::jsonb)
                    RETURNING id
                    """,
        ("ADVoi voice launch", "queue_deep_review", "pending", '{"trigger": "test"}'),
    )


@pytest.mark.asyncio
async def test_list_pending_returns_items(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test")
    created = datetime(2026, 7, 8, 12, 0, tzinfo=UTC)

    fake_connect, _mock_cur = _mock_postgres_cursor(
        fetchall=[
            (1, "First brief", "queue_deep_review", "pending", {"k": "v"}, created),
        ]
    )

    with patch("psycopg.AsyncConnection.connect", side_effect=fake_connect):
        items = await review_queue.list_pending(limit=5)

    assert len(items) == 1
    assert items[0]["queue_id"] == 1
    assert items[0]["title"] == "First brief"
    assert items[0]["brief_url"] == "https://advoi.keyteller.com/briefs/1"
    assert items[0]["created_at"] == created.isoformat()


@pytest.mark.asyncio
async def test_dequeue_review_updates_status(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test")
    created = datetime(2026, 7, 8, 12, 0, tzinfo=UTC)
    fake_connect, mock_cur = _mock_postgres_cursor(
        fetchone=(
            5,
            "Done brief",
            "queue_deep_review",
            review_queue.STATUS_DEQUEUED,
            {},
            created,
        )
    )

    with patch("psycopg.AsyncConnection.connect", side_effect=fake_connect):
        item = await review_queue.dequeue_review(5)

    assert item is not None
    assert item["queue_id"] == 5
    assert item["status"] == "dequeued"
    # Ensure UPDATE targets pending → dequeued
    args = mock_cur.execute.call_args
    assert args is not None
    sql, params = args[0][0], args[0][1]
    assert "UPDATE review_queue" in " ".join(sql.split())
    assert params[0] == review_queue.STATUS_DEQUEUED
    assert params[1] == 5
    assert params[2] == review_queue.STATUS_PENDING


# ---------------------------------------------------------------------------
# In-memory Postgres stand-in — CRUD survives "process restart"
# ---------------------------------------------------------------------------


class _PersistentReviewDb:
    """Shared row store + connect factory. New connections each call simulate redeploy."""

    def __init__(self) -> None:
        self.rows: dict[int, dict[str, Any]] = {}
        self._seq = 0

    def connect_factory(self):
        store = self

        class _Cursor:
            def __init__(self) -> None:
                self._fetchone: Any = None
                self._fetchall: list[Any] = []

            async def execute(self, query: str, params: Any = None) -> None:
                q = " ".join(query.split())
                upper = q.upper()
                params = params or ()

                if upper.startswith("INSERT INTO REVIEW_QUEUE"):
                    store._seq += 1
                    qid = store._seq
                    title, source_frame, status, meta_raw = params
                    meta = json.loads(meta_raw) if isinstance(meta_raw, str) else (meta_raw or {})
                    store.rows[qid] = {
                        "id": qid,
                        "title": title,
                        "source_frame": source_frame,
                        "status": status,
                        "metadata": meta,
                        "created_at": datetime(2026, 7, 10, 12, 0, tzinfo=UTC),
                    }
                    self._fetchone = (qid,)
                    self._fetchall = []
                    return

                if upper.startswith("SELECT") and "WHERE ID = %S" in upper:
                    qid = int(params[0])
                    row = store.rows.get(qid)
                    self._fetchone = _row_tuple(row) if row else None
                    self._fetchall = []
                    return

                if upper.startswith("SELECT") and "STATUS = %S" in upper:
                    status, limit = params[0], int(params[1])
                    pending = [
                        r
                        for r in sorted(store.rows.values(), key=lambda x: x["created_at"])
                        if r["status"] == status
                    ][:limit]
                    self._fetchall = [_row_tuple(r) for r in pending]
                    self._fetchone = None
                    return

                if upper.startswith("UPDATE REVIEW_QUEUE"):
                    new_status, qid, expect_status = params[0], int(params[1]), params[2]
                    row = store.rows.get(qid)
                    if row is None or row["status"] != expect_status:
                        self._fetchone = None
                        self._fetchall = []
                        return
                    row["status"] = new_status
                    self._fetchone = _row_tuple(row)
                    self._fetchall = []
                    return

                raise AssertionError(f"unexpected SQL in fake DB: {q}")

            async def fetchone(self) -> Any:
                return self._fetchone

            async def fetchall(self) -> list[Any]:
                return list(self._fetchall)

        class _Conn:
            def cursor(self):
                return _AsyncContext(_Cursor())

            async def commit(self):
                return None

        async def fake_connect(_dsn: str):
            return _AsyncContext(_Conn())

        return fake_connect


def _row_tuple(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        row["id"],
        row["title"],
        row["source_frame"],
        row["status"],
        row["metadata"],
        row["created_at"],
    )


@pytest.mark.asyncio
async def test_crud_roundtrip_survives_process_restart(monkeypatch):
    """enqueue → list → (restart) → get → dequeue → list empty; shared DB only."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://test-review-queue")
    db = _PersistentReviewDb()

    # Process A: enqueue + list
    with patch("psycopg.AsyncConnection.connect", side_effect=db.connect_factory()):
        qid = await review_queue.enqueue_review(
            "Staging catch-up",
            "queue_deep_review",
            metadata={"trigger": "voice_frame"},
        )
        assert qid is not None
        pending = await review_queue.list_pending()
        assert len(pending) == 1
        assert pending[0]["queue_id"] == qid
        assert pending[0]["title"] == "Staging catch-up"
        assert pending[0]["status"] == review_queue.STATUS_PENDING

    # Process B (API redeploy): new connections, same Postgres rows
    with patch("psycopg.AsyncConnection.connect", side_effect=db.connect_factory()):
        item = await review_queue.get_review_item(qid)
        assert item is not None
        assert item["title"] == "Staging catch-up"
        assert item["metadata"] == {"trigger": "voice_frame"}
        assert item["brief_url"].endswith(f"/{qid}")

        dequeued = await review_queue.dequeue_review(qid)
        assert dequeued is not None
        assert dequeued["status"] == review_queue.STATUS_DEQUEUED
        assert await review_queue.list_pending() == []

        # Second dequeue is a no-op (already dequeued)
        assert await review_queue.dequeue_review(qid) is None

        # Get still returns historical row
        after = await review_queue.get_review_item(qid)
        assert after is not None
        assert after["status"] == review_queue.STATUS_DEQUEUED


@pytest.mark.asyncio
async def test_ensure_table_uses_migration_runner(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test")
    called: list[str] = []

    async def _fake_apply(**_kwargs: Any):
        called.append("apply")
        from advoi.db.migrations import MigrationResult

        return MigrationResult(ok=True, applied=["000_baseline_tables", "002_review_queue_status_idx"])

    monkeypatch.setattr("advoi.db.migrations.apply_pending_migrations", _fake_apply)
    assert await review_queue.ensure_table() is True
    assert called == ["apply"]


# ---------------------------------------------------------------------------
# Frame runner + HTTP API
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_review_queue_mock_includes_brief_url():
    result = await run_frame("queue_deep_review", confirmed=True)
    assert result.status == "ok"
    assert result.detail.get("queued") is True
    assert result.detail.get("brief_url")
    assert "Desktop brief:" in result.spoken_summary


@pytest.mark.asyncio
async def test_run_review_queue_persists_when_database_configured(monkeypatch):
    monkeypatch.delenv("ADVOI_FRAME_MOCK", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://test")

    with (
        patch(
            "advoi.routing.frame_runner._load_open_briefs",
            AsyncMock(return_value=(["Staging catch-up"], "postgres")),
        ),
        patch(
            "advoi.memory.review_queue.enqueue_review",
            AsyncMock(return_value=12),
        ),
    ):
        result = await run_frame("queue_deep_review", confirmed=True)

    assert result.status == "ok"
    assert result.detail["queue_id"] == 12
    assert result.detail["title"] == "Staging catch-up"
    assert "https://advoi.keyteller.com/briefs/12" in result.detail["brief_url"]
    assert "Staging catch-up" in result.spoken_summary


@pytest.mark.asyncio
async def test_run_review_queue_falls_back_without_database(monkeypatch):
    monkeypatch.delenv("ADVOI_FRAME_MOCK", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with patch(
        "advoi.routing.frame_runner._load_open_briefs",
        AsyncMock(return_value=([], "postgres")),
    ):
        result = await run_frame("queue_deep_review", confirmed=True)

    assert result.status == "ok"
    assert result.detail.get("queued") is True
    assert result.detail.get("persistence") == "unavailable"
    assert "surface the brief" in result.spoken_summary


def test_api_review_queue_empty_without_database(client, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    resp = client.get("/api/review-queue")
    assert resp.status_code == 200
    data = resp.json()
    assert data["pending"] == []
    assert data["count"] == 0


def test_api_review_queue_lists_pending(client, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test")
    pending = [
        {
            "queue_id": 3,
            "title": "ADVoi voice launch",
            "source_frame": "queue_deep_review",
            "status": "pending",
            "metadata": {},
            "brief_url": "https://advoi.keyteller.com/briefs/3",
            "created_at": "2026-07-08T12:00:00+00:00",
        }
    ]

    with patch("advoi.memory.review_queue.list_pending", AsyncMock(return_value=pending)):
        resp = client.get("/api/review-queue")

    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    assert data["pending"][0]["queue_id"] == 3


def test_api_review_queue_item_found(client, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test")
    item = {
        "queue_id": 12,
        "title": "Fleet governance review",
        "source_frame": "queue_deep_review",
        "status": "pending",
        "metadata": {},
        "brief_url": "https://advoi.keyteller.com/briefs/12",
        "created_at": "2026-07-08T12:00:00+00:00",
    }

    with patch("advoi.memory.review_queue.get_review_item", AsyncMock(return_value=item)):
        resp = client.get("/api/review-queue/12")

    assert resp.status_code == 200
    assert resp.json()["item"]["queue_id"] == 12


def test_api_review_queue_item_not_found(client, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test")

    with patch("advoi.memory.review_queue.get_review_item", AsyncMock(return_value=None)):
        resp = client.get("/api/review-queue/999")

    assert resp.status_code == 404


def test_api_review_queue_dequeue(client, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test")
    item = {
        "queue_id": 12,
        "title": "Fleet governance review",
        "source_frame": "queue_deep_review",
        "status": "dequeued",
        "metadata": {},
        "brief_url": "https://advoi.keyteller.com/briefs/12",
        "created_at": "2026-07-08T12:00:00+00:00",
    }

    with patch("advoi.memory.review_queue.dequeue_review", AsyncMock(return_value=item)):
        resp = client.post("/api/review-queue/12/dequeue")

    assert resp.status_code == 200
    assert resp.json()["item"]["status"] == "dequeued"


def test_api_review_queue_dequeue_not_found(client, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test")

    with patch("advoi.memory.review_queue.dequeue_review", AsyncMock(return_value=None)):
        resp = client.post("/api/review-queue/999/dequeue")

    assert resp.status_code == 404
