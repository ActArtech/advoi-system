"""PEL gate_snapshot — portfolio_events append and emit script parsing."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from advoi.portfolio.gate_snapshot import emit_gate_snapshot_from_report, parse_gate_report
from advoi.portfolio.pel import append_portfolio_event, ensure_portfolio_events_table


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


def _mock_postgres_cursor(*, fetchone=None):
    mock_cur = AsyncMock()
    mock_cur.fetchone = AsyncMock(return_value=fetchone)

    mock_conn = _FakeConn(mock_cur)

    async def fake_connect(_dsn):
        return _AsyncContext(mock_conn)

    return fake_connect, mock_cur

SAMPLE_GATE_REPORT = """\
# Aether output gate — 2026-07-10 14:30 UTC

**Verdict:** PASS
**Active slug:** advoi
**Project:** /data/projects/advoi
**JSON:** /data/aether-proactive-latest.json

## Checks

| Check | OK | Detail |
|-------|-----|--------|
| lab_clone | yes | /data/projects/advoi |
| findings_present | yes | count=3 actionable=2 |

## Actionable findings (may stage)

- **[HIGH]** [security] rotate staging key
- **[MEDIUM]** [review] update brief copy
"""


@pytest.mark.asyncio
async def test_ensure_portfolio_events_table(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert await ensure_portfolio_events_table() is False

    monkeypatch.setenv("DATABASE_URL", "postgresql://test/db")
    fake_connect, mock_cur = _mock_postgres_cursor()

    with patch("psycopg.AsyncConnection.connect", side_effect=fake_connect):
        assert await ensure_portfolio_events_table() is True
    mock_cur.execute.assert_called()


@pytest.mark.asyncio
async def test_append_portfolio_event_inserts(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test/db")
    fake_connect, mock_cur = _mock_postgres_cursor(fetchone=None)

    payload = {"verdict": "PASS", "timestamp": "2026-07-10 14:30 UTC"}

    with patch("psycopg.AsyncConnection.connect", side_effect=fake_connect):
        ok = await append_portfolio_event("gate_snapshot", payload, venture_slug="advoi")

    assert ok is True
    insert_calls = [
        call
        for call in mock_cur.execute.await_args_list
        if "INSERT INTO portfolio_events" in str(call.args[0])
    ]
    assert insert_calls
    sql, params = insert_calls[0].args
    assert "INSERT INTO portfolio_events" in sql
    assert params[0] == "gate_snapshot"
    assert params[1] == "advoi"
    assert json.loads(params[2]) == payload


@pytest.mark.asyncio
async def test_append_portfolio_event_dedupes_by_timestamp(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test/db")
    fake_connect, mock_cur = _mock_postgres_cursor(fetchone=(1,))

    payload = {"verdict": "PASS", "timestamp": "2026-07-10 14:30 UTC"}

    with patch("psycopg.AsyncConnection.connect", side_effect=fake_connect):
        ok = await append_portfolio_event("gate_snapshot", payload, venture_slug="advoi")

    assert ok is True
    insert_calls = [
        call
        for call in mock_cur.execute.await_args_list
        if "INSERT INTO portfolio_events" in str(call.args[0])
    ]
    assert not insert_calls


def test_parse_gate_report_pass_payload():
    payload = parse_gate_report(
        SAMPLE_GATE_REPORT,
        exit_code=0,
        report_path="/data/aether-gate-latest.md",
    )
    assert payload is not None
    assert payload["verdict"] == "PASS"
    assert payload["slug"] == "advoi"
    assert payload["exit_code"] == 0
    assert payload["actionable_count"] == 2
    assert payload["timestamp"] == "2026-07-10 14:30 UTC"
    assert payload["report_path"] == "/data/aether-gate-latest.md"
    assert any(c["name"] == "lab_clone" for c in payload["checks"])


def test_parse_gate_report_skips_fail_exit_code():
    assert (
        parse_gate_report(
            SAMPLE_GATE_REPORT,
            exit_code=2,
            report_path="/data/aether-gate-latest.md",
        )
        is None
    )


@pytest.mark.asyncio
async def test_emit_gate_snapshot_calls_append(tmp_path, monkeypatch):
    report = tmp_path / "aether-gate-latest.md"
    report.write_text(SAMPLE_GATE_REPORT, encoding="utf-8")

    mock_append = AsyncMock(return_value=True)
    monkeypatch.setattr("advoi.portfolio.pel.append_portfolio_event", mock_append)

    ok = await emit_gate_snapshot_from_report(str(report), 1)
    assert ok is True
    mock_append.assert_awaited_once()
    event_type, payload = mock_append.await_args.args[:2]
    assert event_type == "gate_snapshot"
    assert payload["verdict"] == "PASS"
    assert payload["exit_code"] == 1
    assert mock_append.await_args.kwargs.get("venture_slug") == "advoi"