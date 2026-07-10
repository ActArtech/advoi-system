"""T0: Redis voice-turn TTL helpers + memory_events retention cutoff logic."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from advoi.memory.postgres_store import (
    DEFAULT_MEMORY_EVENTS_RETENTION_DAYS,
    MIN_MEMORY_EVENTS_RETENTION_DAYS,
    memory_events_retention_cutoff,
    memory_events_retention_days,
)
from advoi.memory.redis_store import (
    DEFAULT_EPHEMERAL_TTL_SEC,
    DEFAULT_MAX_TURNS,
    ephemeral_max_turns,
    ephemeral_ttl_sec,
)


def test_ephemeral_ttl_default(monkeypatch):
    monkeypatch.delenv("ADVOI_REDIS_VOICE_TTL_SEC", raising=False)
    assert ephemeral_ttl_sec() == DEFAULT_EPHEMERAL_TTL_SEC
    assert DEFAULT_EPHEMERAL_TTL_SEC == 3600


def test_ephemeral_ttl_from_env(monkeypatch):
    monkeypatch.setenv("ADVOI_REDIS_VOICE_TTL_SEC", "7200")
    assert ephemeral_ttl_sec() == 7200


@pytest.mark.parametrize("bad", ["", "0", "-5", "nope", "  "])
def test_ephemeral_ttl_invalid_falls_back(monkeypatch, bad):
    monkeypatch.setenv("ADVOI_REDIS_VOICE_TTL_SEC", bad)
    assert ephemeral_ttl_sec() == DEFAULT_EPHEMERAL_TTL_SEC


def test_ephemeral_max_turns_default_and_env(monkeypatch):
    monkeypatch.delenv("ADVOI_REDIS_VOICE_MAX_TURNS", raising=False)
    assert ephemeral_max_turns() == DEFAULT_MAX_TURNS
    assert DEFAULT_MAX_TURNS == 5
    monkeypatch.setenv("ADVOI_REDIS_VOICE_MAX_TURNS", "3")
    assert ephemeral_max_turns() == 3


def test_memory_events_retention_days_default(monkeypatch):
    monkeypatch.delenv("ADVOI_MEMORY_EVENTS_RETENTION_DAYS", raising=False)
    assert memory_events_retention_days() == DEFAULT_MEMORY_EVENTS_RETENTION_DAYS
    assert DEFAULT_MEMORY_EVENTS_RETENTION_DAYS == 90


def test_memory_events_retention_days_env_and_floor(monkeypatch):
    monkeypatch.setenv("ADVOI_MEMORY_EVENTS_RETENTION_DAYS", "120")
    assert memory_events_retention_days() == 120
    # Below floor → floor (safe default for accidental short windows)
    monkeypatch.setenv("ADVOI_MEMORY_EVENTS_RETENTION_DAYS", "1")
    assert memory_events_retention_days() == MIN_MEMORY_EVENTS_RETENTION_DAYS
    assert MIN_MEMORY_EVENTS_RETENTION_DAYS == 7


def test_retention_cutoff_pure_math():
    now = datetime(2026, 7, 10, 12, 0, 0, tzinfo=timezone.utc)
    cut = memory_events_retention_cutoff(now=now, retention_days=90)
    assert cut == now - timedelta(days=90)
    assert cut.tzinfo == timezone.utc


def test_retention_cutoff_naive_now_assumes_utc():
    now = datetime(2026, 1, 1, 0, 0, 0)  # naive
    cut = memory_events_retention_cutoff(now=now, retention_days=7)
    assert cut == datetime(2025, 12, 25, 0, 0, 0, tzinfo=timezone.utc)


def test_retention_cutoff_rejects_non_positive():
    with pytest.raises(ValueError, match="retention_days"):
        memory_events_retention_cutoff(retention_days=0)


@pytest.mark.asyncio
async def test_prune_memory_events_missing_dsn(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    from advoi.memory.postgres_store import prune_memory_events

    result = await prune_memory_events(dry_run=True, retention_days=90)
    assert result["ok"] is False
    assert result["dry_run"] is True
    assert result["matched"] == 0
    assert result["deleted"] == 0
    assert "DATABASE_URL" in result.get("error", "")
    assert result["retention_days"] == 90
    # cutoff is ISO and ~90 days ago
    cut = datetime.fromisoformat(result["cutoff"])
    assert cut.tzinfo is not None
    assert cut < datetime.now(timezone.utc) - timedelta(days=89)
