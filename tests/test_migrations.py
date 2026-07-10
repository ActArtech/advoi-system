"""T0: versioned SQL migration runner (deploy/migrations/ + API boot apply)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from advoi.db.migrations import (
    MigrationFile,
    apply_migration_file,
    apply_pending_migrations,
    file_checksum,
    list_migration_files,
    migrations_dir,
    split_sql_statements,
)

# ---------------------------------------------------------------------------
# Discovery / ordering
# ---------------------------------------------------------------------------


def test_migrations_dir_contains_baseline_and_pel():
    root = migrations_dir()
    assert root.is_dir(), f"missing migrations dir: {root}"
    names = {p.name for p in root.glob("*.sql")}
    assert "000_baseline_tables.sql" in names
    assert "001_portfolio_events.sql" in names
    assert "002_review_queue_status_idx.sql" in names


def test_list_migration_files_ordered_by_ordinal():
    files = list_migration_files()
    assert len(files) >= 3
    versions = [m.version for m in files]
    assert versions[0] == "000_baseline_tables"
    assert versions[1] == "001_portfolio_events"
    assert versions[2] == "002_review_queue_status_idx"
    ordinals = [m.ordinal for m in files]
    assert ordinals == sorted(ordinals)
    # Apply order contract used by docs / staging verification
    assert ordinals[0] < ordinals[1] < ordinals[2]


def test_list_migration_files_ignores_non_versioned(tmp_path: Path):
    (tmp_path / "readme.sql").write_text("SELECT 1;", encoding="utf-8")
    (tmp_path / "002_ok.sql").write_text("SELECT 1;", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("x", encoding="utf-8")
    files = list_migration_files(tmp_path)
    assert [m.version for m in files] == ["002_ok"]


def test_list_migration_files_empty_dir(tmp_path: Path):
    assert list_migration_files(tmp_path) == []


# ---------------------------------------------------------------------------
# SQL splitter
# ---------------------------------------------------------------------------


def test_split_sql_statements_basic():
    script = """
    CREATE TABLE a (id int);
    CREATE INDEX i ON a (id);
    """
    stmts = split_sql_statements(script)
    assert len(stmts) == 2
    assert "CREATE TABLE a" in stmts[0]
    assert "CREATE INDEX i" in stmts[1]


def test_split_sql_statements_ignores_semicolons_in_strings_and_comments():
    script = """
    -- comment with ; inside
    INSERT INTO t (x) VALUES ('a;b');
    /* block; comment */
    SELECT "col;name" FROM t;
    """
    stmts = split_sql_statements(script)
    assert len(stmts) == 2
    assert "'a;b'" in stmts[0]
    assert '"col;name"' in stmts[1]


def test_split_sql_statements_dollar_quotes():
    script = """
    DO $$
    BEGIN
      PERFORM 1;
    END
    $$;
    SELECT 2;
    """
    stmts = split_sql_statements(script)
    assert len(stmts) == 2
    assert "DO $$" in stmts[0]
    assert "SELECT 2" in stmts[1]


def test_real_baseline_migration_splits():
    path = migrations_dir() / "000_baseline_tables.sql"
    stmts = split_sql_statements(path.read_text(encoding="utf-8"))
    assert len(stmts) == 3
    joined = "\n".join(stmts).upper()
    assert "MEMORY_EVENTS" in joined
    assert "DECISION_BRIEFS" in joined
    assert "REVIEW_QUEUE" in joined


def test_real_pel_migration_splits():
    path = migrations_dir() / "001_portfolio_events.sql"
    stmts = split_sql_statements(path.read_text(encoding="utf-8"))
    # table + 4 indexes + backfill insert
    assert len(stmts) >= 5
    assert any("portfolio_events" in s and "CREATE TABLE" in s.upper() for s in stmts)


# ---------------------------------------------------------------------------
# Apply / idempotency (fake cursor — no Postgres)
# ---------------------------------------------------------------------------


class _FakeCursor:
    """Minimal async cursor recording executes for T0 without DATABASE_URL."""

    def __init__(self) -> None:
        self.executed: list[tuple[str, Any]] = []
        self._applied: set[str] = set()
        self._fetch: list[Any] = []

    async def execute(self, query: str, params: Any = None) -> None:
        q = " ".join(query.split())
        self.executed.append((q, params))
        upper = q.upper()
        if "CREATE TABLE IF NOT EXISTS SCHEMA_MIGRATIONS" in upper:
            return
        if upper.startswith("SELECT VERSION FROM SCHEMA_MIGRATIONS"):
            self._fetch = [(v,) for v in sorted(self._applied)]
            return
        if upper.startswith("INSERT INTO SCHEMA_MIGRATIONS"):
            version = params[0] if params else None
            if version:
                self._applied.add(str(version))
            self._fetch = []
            return
        # Migration DDL/DML — record only
        self._fetch = []

    async def fetchall(self) -> list[Any]:
        return list(self._fetch)

    async def fetchone(self) -> Any:
        return self._fetch[0] if self._fetch else None


@pytest.mark.asyncio
async def test_apply_pending_no_database_url(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    (tmp_path / "001_x.sql").write_text("SELECT 1;", encoding="utf-8")
    result = await apply_pending_migrations(directory=tmp_path)
    assert result.ok is True
    assert result.reason == "no_database_url"
    assert result.applied == []
    assert result.pending == ["001_x"]


@pytest.mark.asyncio
async def test_apply_pending_idempotent_with_fake_cursor(tmp_path: Path):
    (tmp_path / "000_a.sql").write_text(
        "CREATE TABLE IF NOT EXISTS a (id int);\nCREATE INDEX IF NOT EXISTS a_idx ON a (id);",
        encoding="utf-8",
    )
    (tmp_path / "001_b.sql").write_text(
        "CREATE TABLE IF NOT EXISTS b (id int);",
        encoding="utf-8",
    )
    cur = _FakeCursor()

    first = await apply_pending_migrations(directory=tmp_path, cur=cur)
    assert first.ok is True
    assert first.applied == ["000_a", "001_b"]
    assert first.skipped == []
    assert cur._applied == {"000_a", "001_b"}

    second = await apply_pending_migrations(directory=tmp_path, cur=cur)
    assert second.ok is True
    assert second.applied == []
    assert second.skipped == ["000_a", "001_b"]


@pytest.mark.asyncio
async def test_apply_migration_file_records_checksum(tmp_path: Path):
    path = tmp_path / "003_only.sql"
    path.write_text("SELECT 42;", encoding="utf-8")
    mig = MigrationFile(path=path, version="003_only", ordinal=3)
    cur = _FakeCursor()
    await apply_migration_file(cur, mig)
    assert "003_only" in cur._applied
    inserts = [p for q, p in cur.executed if p and "SCHEMA_MIGRATIONS" in q.upper()]
    assert inserts
    version, checksum = inserts[-1]
    assert version == "003_only"
    assert checksum == file_checksum(path)


@pytest.mark.asyncio
async def test_apply_real_migrations_order_on_fake_cursor():
    """Walk shipped deploy/migrations/ through the runner (DDL recorded, not executed on PG)."""
    cur = _FakeCursor()
    result = await apply_pending_migrations(cur=cur)
    assert result.ok is True
    assert result.applied[0] == "000_baseline_tables"
    assert result.applied[1] == "001_portfolio_events"
    assert result.applied[2] == "002_review_queue_status_idx"
    # Tracking inserts for all versions
    assert cur._applied == {
        "000_baseline_tables",
        "001_portfolio_events",
        "002_review_queue_status_idx",
    }
    # Ensure CREATE TABLE fragments from both files were executed
    blob = "\n".join(q for q, _ in cur.executed).upper()
    assert "MEMORY_EVENTS" in blob
    assert "PORTFOLIO_EVENTS" in blob
    assert "REVIEW_QUEUE_STATUS_CREATED_AT_IDX" in blob
    assert "SCHEMA_MIGRATIONS" in blob


@pytest.mark.asyncio
async def test_ensure_portfolio_events_table_uses_runner(monkeypatch: pytest.MonkeyPatch):
    from advoi.analytics import pel

    called: list[str] = []

    async def _fake_apply(**kwargs: Any):
        called.append("apply")
        from advoi.db.migrations import MigrationResult

        return MigrationResult(ok=True, applied=["000_baseline_tables", "001_portfolio_events"])

    monkeypatch.setattr("advoi.db.migrations.apply_pending_migrations", _fake_apply)
    ok = await pel.ensure_portfolio_events_table()
    assert ok is True
    assert called == ["apply"]


def test_apply_order_documented_contract():
    """Documented apply order: baseline (000) then PEL (001) then review_queue idx (002)."""
    files = list_migration_files()
    by_version = {m.version: m for m in files}
    assert "000_baseline_tables" in by_version
    assert "001_portfolio_events" in by_version
    assert "002_review_queue_status_idx" in by_version
    assert by_version["000_baseline_tables"].ordinal < by_version["001_portfolio_events"].ordinal
    assert (
        by_version["001_portfolio_events"].ordinal
        < by_version["002_review_queue_status_idx"].ordinal
    )


def test_review_queue_index_migration_splits():
    path = migrations_dir() / "002_review_queue_status_idx.sql"
    stmts = split_sql_statements(path.read_text(encoding="utf-8"))
    assert len(stmts) == 1
    assert "review_queue_status_created_at_idx" in stmts[0]
