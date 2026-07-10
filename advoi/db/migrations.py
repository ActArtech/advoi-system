"""Versioned SQL migration runner for deploy/migrations/.

Apply order is lexicographic filename order (``000_…`` before ``001_…``).
Each file is applied once; progress is recorded in ``schema_migrations``.
SQL files should use idempotent DDL (``IF NOT EXISTS`` / ``ON CONFLICT DO NOTHING``)
so manual re-runs and partial applies remain safe.

API boot calls :func:`apply_pending_migrations` when ``DATABASE_URL`` is set.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_LOGGER = logging.getLogger(__name__)

_SCHEMA_MIGRATIONS_DDL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version     TEXT PRIMARY KEY,
    checksum    TEXT NOT NULL,
    applied_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
"""

# Filenames: NNN_description.sql (leading digits required).
_MIGRATION_NAME_RE = re.compile(r"^(\d+)_([a-z0-9_]+)\.sql$", re.IGNORECASE)


@dataclass(frozen=True)
class MigrationFile:
    """One versioned SQL file under deploy/migrations/."""

    path: Path
    version: str  # stem, e.g. 001_portfolio_events
    ordinal: int  # leading number for sort stability

    @property
    def filename(self) -> str:
        return self.path.name


@dataclass
class MigrationResult:
    """Outcome of one apply_pending_migrations call."""

    applied: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    pending: list[str] = field(default_factory=list)
    ok: bool = True
    reason: str | None = None  # set when skipped/failed without DB work

    @property
    def applied_count(self) -> int:
        return len(self.applied)


def migrations_dir() -> Path:
    """Resolve deploy/migrations directory.

    Order:
    1. ``ADVOI_MIGRATIONS_DIR`` env override
    2. repo-relative path from this package (dev / hatch install editable)
    3. ``/app/deploy/migrations`` (API container layout)
    4. ``cwd/deploy/migrations``
    """
    env = (os.getenv("ADVOI_MIGRATIONS_DIR") or "").strip()
    if env:
        return Path(env)

    # advoi/db/migrations.py → parents[2] == repo root when running from source tree
    repo_candidate = Path(__file__).resolve().parents[2] / "deploy" / "migrations"
    candidates = (
        repo_candidate,
        Path("/app/deploy/migrations"),
        Path.cwd() / "deploy" / "migrations",
    )
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return repo_candidate


def list_migration_files(directory: Path | None = None) -> list[MigrationFile]:
    """Return migration files sorted by ordinal then name. Ignores non-matching files."""
    root = directory if directory is not None else migrations_dir()
    if not root.is_dir():
        return []

    found: list[MigrationFile] = []
    for path in sorted(root.iterdir()):
        if not path.is_file() or path.suffix.lower() != ".sql":
            continue
        match = _MIGRATION_NAME_RE.match(path.name)
        if not match:
            _LOGGER.warning("skipping non-versioned SQL file: %s", path.name)
            continue
        ordinal = int(match.group(1))
        found.append(MigrationFile(path=path, version=path.stem, ordinal=ordinal))
    found.sort(key=lambda m: (m.ordinal, m.version))
    return found


def split_sql_statements(script: str) -> list[str]:
    """Split a SQL script into statements on ';' outside quotes/comments.

    Handles ``--`` line comments, ``/* */`` block comments, single- and double-quoted
    strings, and dollar-quoted blocks (``$$`` / ``$tag$``).
    """
    statements: list[str] = []
    buf: list[str] = []
    i = 0
    n = len(script)
    in_single = False
    in_double = False
    in_line_comment = False
    in_block_comment = False
    dollar_tag: str | None = None

    while i < n:
        ch = script[i]
        nxt = script[i + 1] if i + 1 < n else ""

        if in_line_comment:
            buf.append(ch)
            if ch == "\n":
                in_line_comment = False
            i += 1
            continue

        if in_block_comment:
            buf.append(ch)
            if ch == "*" and nxt == "/":
                buf.append(nxt)
                i += 2
                in_block_comment = False
                continue
            i += 1
            continue

        if dollar_tag is not None:
            if script.startswith(dollar_tag, i):
                buf.append(dollar_tag)
                i += len(dollar_tag)
                dollar_tag = None
                continue
            buf.append(ch)
            i += 1
            continue

        if in_single:
            buf.append(ch)
            if ch == "'" and nxt == "'":
                buf.append(nxt)
                i += 2
                continue
            if ch == "'":
                in_single = False
            i += 1
            continue

        if in_double:
            buf.append(ch)
            if ch == '"' and nxt == '"':
                buf.append(nxt)
                i += 2
                continue
            if ch == '"':
                in_double = False
            i += 1
            continue

        # not inside any quote/comment
        if ch == "-" and nxt == "-":
            buf.append(ch)
            buf.append(nxt)
            i += 2
            in_line_comment = True
            continue
        if ch == "/" and nxt == "*":
            buf.append(ch)
            buf.append(nxt)
            i += 2
            in_block_comment = True
            continue
        if ch == "'":
            buf.append(ch)
            in_single = True
            i += 1
            continue
        if ch == '"':
            buf.append(ch)
            in_double = True
            i += 1
            continue
        if ch == "$":
            # dollar-quote: $tag$ … $tag$
            m = re.match(r"\$([A-Za-z_][A-Za-z0-9_]*)?\$", script[i:])
            if m:
                tag = m.group(0)
                buf.append(tag)
                dollar_tag = tag
                i += len(tag)
                continue

        if ch == ";":
            stmt = "".join(buf).strip()
            if stmt:
                statements.append(stmt)
            buf = []
            i += 1
            continue

        buf.append(ch)
        i += 1

    tail = "".join(buf).strip()
    if tail:
        statements.append(tail)
    # Drop pure-comment / empty fragments
    cleaned: list[str] = []
    for stmt in statements:
        body = _strip_sql_comments(stmt).strip()
        if body:
            cleaned.append(stmt)
    return cleaned


def _strip_sql_comments(stmt: str) -> str:
    """Remove comments for emptiness checks only."""
    no_block = re.sub(r"/\*.*?\*/", "", stmt, flags=re.DOTALL)
    lines = []
    for line in no_block.splitlines():
        if "--" in line:
            line = line[: line.index("--")]
        lines.append(line)
    return "\n".join(lines)


def file_checksum(path: Path) -> str:
    """SHA-256 hex digest of file bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


async def _ensure_tracking_table(cur: Any) -> None:
    await cur.execute(_SCHEMA_MIGRATIONS_DDL)


async def _applied_versions(cur: Any) -> set[str]:
    await cur.execute("SELECT version FROM schema_migrations")
    rows = await cur.fetchall()
    return {str(row[0]) for row in rows if row and row[0]}


async def _record_applied(cur: Any, version: str, checksum: str) -> None:
    await cur.execute(
        """
        INSERT INTO schema_migrations (version, checksum)
        VALUES (%s, %s)
        ON CONFLICT (version) DO NOTHING
        """,
        (version, checksum),
    )


async def apply_migration_file(cur: Any, migration: MigrationFile) -> None:
    """Execute one migration file's statements on an open cursor (no commit)."""
    script = migration.path.read_text(encoding="utf-8")
    for statement in split_sql_statements(script):
        await cur.execute(statement)
    await _record_applied(cur, migration.version, file_checksum(migration.path))


async def apply_pending_migrations(
    *,
    dsn: str | None = None,
    directory: Path | None = None,
    cur: Any | None = None,
    conn: Any | None = None,
) -> MigrationResult:
    """Apply all pending ``*.sql`` migrations in order.

    Parameters
    ----------
    dsn:
        Postgres URL. Defaults to ``DATABASE_URL``. When empty and no ``cur``/
        ``conn`` is provided, returns a no-op success result.
    directory:
        Override migrations directory (tests).
    cur / conn:
        Optional open psycopg async cursor/connection for tests. When ``cur`` is
        given, the caller owns the transaction (no connect/commit). When only
        ``conn`` is given, this function commits after all applies.

    Idempotent: already-recorded versions in ``schema_migrations`` are skipped.
    """
    files = list_migration_files(directory)
    if not files:
        return MigrationResult(ok=True, reason="no_migration_files")

    # Injected cursor path (unit tests / shared txn)
    if cur is not None:
        await _ensure_tracking_table(cur)
        done = await _applied_versions(cur)
        result = MigrationResult()
        for mig in files:
            if mig.version in done:
                result.skipped.append(mig.version)
                continue
            await apply_migration_file(cur, mig)
            result.applied.append(mig.version)
            done.add(mig.version)
        result.pending = []
        return result

    # Injected connection path
    if conn is not None:
        async with conn.cursor() as db_cur:
            result = await apply_pending_migrations(directory=directory, cur=db_cur)
        await conn.commit()
        return result

    resolved_dsn = (dsn if dsn is not None else os.getenv("DATABASE_URL", "")).strip()
    if not resolved_dsn:
        return MigrationResult(
            ok=True,
            reason="no_database_url",
            pending=[m.version for m in files],
        )

    try:
        import psycopg

        async with await psycopg.AsyncConnection.connect(resolved_dsn) as db_conn:
            async with db_conn.cursor() as db_cur:
                result = await apply_pending_migrations(directory=directory, cur=db_cur)
            await db_conn.commit()
        if result.applied:
            _LOGGER.info(
                "applied %s migration(s): %s",
                result.applied_count,
                ", ".join(result.applied),
            )
        elif result.skipped:
            _LOGGER.debug(
                "migrations already applied (%s skipped)",
                len(result.skipped),
            )
        return result
    except Exception as exc:
        _LOGGER.warning("migration apply deferred: %s", exc)
        return MigrationResult(
            ok=False,
            reason=f"error:{exc}",
            pending=[m.version for m in files],
        )
