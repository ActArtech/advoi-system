"""T0: Brief Curator PG-canonical / Redis-cache-only (ADR-026 ship #2b)."""

from __future__ import annotations

import json

import pytest

from advoi.copy_style import format_briefs_spoken
from advoi.memory.briefs_cache import OPEN_BRIEFS_KEY


class _FakeRedis:
    """Minimal Redis stand-in for cache invalidate/fill/read tests."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.delete_calls: list[str] = []
        self.set_calls: list[tuple[str, str]] = []

    def get(self, key: str) -> str | None:
        return self.store.get(key)

    def set(self, key: str, value: str) -> bool:
        self.store[key] = value
        self.set_calls.append((key, value))
        return True

    def delete(self, key: str) -> int:
        self.delete_calls.append(key)
        existed = 1 if key in self.store else 0
        self.store.pop(key, None)
        return existed


@pytest.fixture
def fake_redis(monkeypatch: pytest.MonkeyPatch) -> _FakeRedis:
    client = _FakeRedis()
    # briefs_cache imports get_redis from redis_client inside each function
    monkeypatch.setattr("advoi.cache.redis_client.get_redis", lambda: client)
    return client


@pytest.mark.asyncio
async def test_upsert_open_brief_invalidates_cache(
    fake_redis: _FakeRedis, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Real upsert_open_brief invalidates Redis after a successful PG commit."""
    fake_redis.store[OPEN_BRIEFS_KEY] = json.dumps(["stale"])

    class _Cur:
        async def execute(self, *_a, **_k):
            return None

    class _CurCtx:
        async def __aenter__(self):
            return _Cur()

        async def __aexit__(self, *exc):
            return False

    class _Conn:
        def cursor(self):
            return _CurCtx()

        async def commit(self):
            return None

    class _ConnCtx:
        async def __aenter__(self):
            return _Conn()

        async def __aexit__(self, *exc):
            return False

    class _FakePsycopg:
        class AsyncConnection:
            @staticmethod
            async def connect(_dsn: str):
                return _ConnCtx()

    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    monkeypatch.setitem(__import__("sys").modules, "psycopg", _FakePsycopg())

    from advoi.memory.postgres_store import upsert_open_brief

    assert await upsert_open_brief("Canonical title from PG") is True
    assert OPEN_BRIEFS_KEY in fake_redis.delete_calls
    assert OPEN_BRIEFS_KEY not in fake_redis.store


@pytest.mark.asyncio
async def test_spoken_uses_pg_when_redis_empty(
    fake_redis: _FakeRedis, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Spoken summary uses Postgres titles when Redis cache is empty."""
    assert fake_redis.store.get(OPEN_BRIEFS_KEY) is None

    pg_titles = [
        "ADVoi voice launch",
        "Staging catch-up",
    ]

    async def _list_open(*, limit: int = 10):
        return list(pg_titles)

    monkeypatch.setattr(
        "advoi.memory.postgres_store.list_open_briefs",
        _list_open,
    )
    monkeypatch.setenv("ADVOI_FRAME_MOCK", "false")

    from advoi.routing.frame_runner import _load_open_briefs, _run_brief_curator

    items, source = await _load_open_briefs()
    assert source == "postgres"
    assert items == pg_titles
    # Cache filled from PG after read
    assert OPEN_BRIEFS_KEY in fake_redis.store
    assert json.loads(fake_redis.store[OPEN_BRIEFS_KEY]) == pg_titles

    spoken, detail = await _run_brief_curator()
    assert detail["source"] == "postgres"
    assert detail["briefs"] == pg_titles
    assert spoken == format_briefs_spoken(pg_titles)
    assert "ADVoi voice launch" in spoken
    # Stale redis-only titles must not appear (cache was empty before fill)
    assert "stale" not in spoken.lower()


@pytest.mark.asyncio
async def test_does_not_merge_stale_redis_with_pg(
    fake_redis: _FakeRedis, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Redis titles that are not in PG are not merged into spoken briefs."""
    fake_redis.store[OPEN_BRIEFS_KEY] = json.dumps(["Stale redis-only brief"])

    async def _list_open(*, limit: int = 10):
        return ["Only postgres brief"]

    monkeypatch.setattr("advoi.memory.postgres_store.list_open_briefs", _list_open)
    monkeypatch.setenv("ADVOI_FRAME_MOCK", "false")

    from advoi.routing.frame_runner import _run_brief_curator

    spoken, detail = await _run_brief_curator()
    assert detail["source"] == "postgres"
    assert detail["briefs"] == ["Only postgres brief"]
    assert "Stale redis-only" not in spoken
    assert "Only postgres brief" in spoken
    # Cache rewritten to PG mirror
    assert json.loads(fake_redis.store[OPEN_BRIEFS_KEY]) == ["Only postgres brief"]


@pytest.mark.asyncio
async def test_pg_empty_clears_cache_no_stale_merge(
    fake_redis: _FakeRedis, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_redis.store[OPEN_BRIEFS_KEY] = json.dumps(["Ghost brief"])

    async def _list_open(*, limit: int = 10):
        return []

    async def _no_recall(*_a, **_k):
        class R:
            strategic: list = []
            operational: list = []
            ephemeral: list = []

        return R()

    monkeypatch.setattr("advoi.memory.postgres_store.list_open_briefs", _list_open)
    monkeypatch.setenv("ADVOI_FRAME_MOCK", "false")

    from advoi.memory import MemoryRouter
    from advoi.routing import frame_runner

    monkeypatch.setattr(MemoryRouter, "recall", _no_recall)
    monkeypatch.setattr(frame_runner, "MemoryRouter", MemoryRouter)

    spoken, detail = await frame_runner._run_brief_curator()
    assert detail["briefs"] == []
    assert OPEN_BRIEFS_KEY not in fake_redis.store
    assert "Ghost" not in spoken


def test_event_write_map_decision_brief_postgres_only() -> None:
    """decision_brief remains Postgres-only (seed must not use it for Hindsight)."""
    from advoi.memory.write_targets import MemoryEventType, WriteTarget, targets_for

    assert targets_for(MemoryEventType.DECISION_BRIEF) == (WriteTarget.POSTGRES,)
    assert WriteTarget.HINDSIGHT not in targets_for(MemoryEventType.DECISION_BRIEF)
    assert WriteTarget.REDIS not in targets_for(MemoryEventType.DECISION_BRIEF)
