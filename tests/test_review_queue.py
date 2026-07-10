"""Review queue persistence and API tests."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from advoi.memory import review_queue
from advoi.routing.frame_runner import run_frame


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
async def test_ensure_table_without_database(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert await review_queue.ensure_table() is False


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
                    VALUES (%s, %s, 'pending', %s::jsonb)
                    RETURNING id
                    """,
        ("ADVoi voice launch", "queue_deep_review", '{"trigger": "test"}'),
    )


@pytest.mark.asyncio
async def test_list_pending_returns_items(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test")
    created = datetime(2026, 7, 8, 12, 0, tzinfo=timezone.utc)

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