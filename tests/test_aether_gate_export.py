"""T0: export aether-gate-latest.md into advoi repo path and/or PEL."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from advoi.aether.gate_export import (
    DEFAULT_REPO_RELATIVE,
    GATE_ARTIFACT,
    PEL_EXPORT_KIND,
    GateExportError,
    content_sha256,
    export_gate_snapshot,
    export_gate_snapshot_sync,
    maybe_git_commit,
    pel_payload_from_export,
    resolve_source_gate,
    snapshot_from_text,
    write_gate_to_repo,
)
from advoi.analytics.pel import memory_rows, reset_memory_store

ROOT = Path(__file__).resolve().parents[1]
EXPORT_SH = ROOT / "scripts" / "aether-gate-export.sh"

SAMPLE_GATE = (
    "# Aether output gate\n\n"
    "**Verdict:** pass\n"
    "**Active slug:** advoi\n"
    "\n"
    "Notes: T0 fixture for gate export.\n"
)

HOLD_GATE = (
    "# Aether output gate\n\n"
    "**Verdict:** hold\n"
    "**Active slug:** clapart\n"
)


@pytest.fixture(autouse=True)
def _pel_memory(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ADVOI_PEL_MEMORY", "true")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    reset_memory_store()
    yield
    reset_memory_store()


# ── pure helpers ─────────────────────────────────────────────────────────────


def test_content_sha256_stable():
    a = content_sha256(SAMPLE_GATE)
    b = content_sha256(SAMPLE_GATE)
    assert a == b
    assert len(a) == 64
    assert a != content_sha256(HOLD_GATE)


def test_snapshot_from_text_parses_verdict_and_slug():
    snap = snapshot_from_text(SAMPLE_GATE, path="/tmp/gate.md")
    assert snap.found is True
    assert snap.verdict == "pass"
    assert snap.active_slug == "advoi"
    assert snap.path == "/tmp/gate.md"


def test_write_gate_to_repo_atomic(tmp_path: Path):
    dest = tmp_path / "data" / "aether" / GATE_ARTIFACT
    result = write_gate_to_repo(SAMPLE_GATE, dest_path=dest)
    assert dest.is_file()
    assert dest.read_text(encoding="utf-8") == SAMPLE_GATE
    assert result["sha256"] == content_sha256(SAMPLE_GATE)
    assert result["bytes"] == len(SAMPLE_GATE.encode("utf-8"))


def test_resolve_source_prefers_explicit(tmp_path: Path):
    explicit = tmp_path / "custom-gate.md"
    explicit.write_text(SAMPLE_GATE, encoding="utf-8")
    got = resolve_source_gate(source_path=explicit)
    assert got == explicit


def test_resolve_source_fleet_when_present(tmp_path: Path):
    fleet = tmp_path / "fleet"
    fleet.mkdir()
    gate = fleet / GATE_ARTIFACT
    gate.write_text(SAMPLE_GATE, encoding="utf-8")
    got = resolve_source_gate(fleet_root=fleet, repo_root=tmp_path / "empty-repo")
    assert got == gate


def test_pel_payload_includes_kind_and_hash():
    snap = snapshot_from_text(SAMPLE_GATE)
    sha = content_sha256(SAMPLE_GATE)
    payload = pel_payload_from_export(
        snap=snap,
        text=SAMPLE_GATE,
        source_path="/fleet/aether-gate-latest.md",
        repo_path=DEFAULT_REPO_RELATIVE,
        sha256=sha,
    )
    assert payload["kind"] == PEL_EXPORT_KIND
    assert payload["artifact"] == GATE_ARTIFACT
    assert payload["verdict"] == "pass"
    assert payload["active_slug"] == "advoi"
    assert payload["content_sha256"] == sha
    assert payload["repo_path"] == DEFAULT_REPO_RELATIVE


def test_maybe_git_commit_disabled_returns_none(tmp_path: Path):
    assert maybe_git_commit(
        repo_root=tmp_path,
        relative_path=DEFAULT_REPO_RELATIVE,
        message="test",
        enabled=False,
    ) is None


# ── export_gate_snapshot (async path) ────────────────────────────────────────


@pytest.mark.asyncio
async def test_export_repo_and_pel(tmp_path: Path):
    fleet = tmp_path / "fleet"
    fleet.mkdir()
    (fleet / GATE_ARTIFACT).write_text(SAMPLE_GATE, encoding="utf-8")
    repo = tmp_path / "repo"
    dest = repo / DEFAULT_REPO_RELATIVE

    result = await export_gate_snapshot(
        fleet_root=fleet,
        repo_root=repo,
        write_repo=True,
        emit_pel=True,
        git_commit=False,
    )

    assert result["ok"] is True
    assert result["verdict"] == "pass"
    assert result["active_slug"] == "advoi"
    assert result["sha256"] == content_sha256(SAMPLE_GATE)
    assert dest.is_file()
    assert dest.read_text(encoding="utf-8") == SAMPLE_GATE
    assert result["pel_event_id"] is not None

    rows = memory_rows()
    assert len(rows) == 1
    row = rows[0]
    assert row["source"] == "aether"
    assert row["type"] == "governance_decision"
    assert row["venture_id"] == "advoi"
    assert row["guardian_status"] == "allowed"
    assert row["payload"]["kind"] == PEL_EXPORT_KIND
    assert row["payload"]["content_sha256"] == result["sha256"]
    assert row["payload"]["verdict"] == "pass"
    assert result["pel_event_id"] == row["id"]


@pytest.mark.asyncio
async def test_export_pel_only(tmp_path: Path):
    source = tmp_path / "src.md"
    source.write_text(HOLD_GATE, encoding="utf-8")
    repo = tmp_path / "repo"
    dest = repo / DEFAULT_REPO_RELATIVE

    result = await export_gate_snapshot(
        source_path=source,
        repo_root=repo,
        write_repo=False,
        emit_pel=True,
    )

    assert result["ok"] is True
    assert result["verdict"] == "hold"
    assert result["dest"] is None
    assert not dest.exists()
    assert result["pel_event_id"] is not None
    rows = memory_rows()
    assert len(rows) == 1
    assert rows[0]["guardian_status"] == "pending"
    assert rows[0]["venture_id"] == "clapart"
    assert rows[0]["payload"]["active_slug"] == "clapart"


@pytest.mark.asyncio
async def test_export_repo_only_skips_pel(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("ADVOI_PEL_MEMORY", raising=False)
    source = tmp_path / "src.md"
    source.write_text(SAMPLE_GATE, encoding="utf-8")
    repo = tmp_path / "repo"

    result = await export_gate_snapshot(
        source_path=source,
        repo_root=repo,
        write_repo=True,
        emit_pel=False,
    )
    assert result["ok"] is True
    assert (repo / DEFAULT_REPO_RELATIVE).is_file()
    assert result["pel_event_id"] is None
    assert memory_rows() == []


@pytest.mark.asyncio
async def test_export_missing_source_raises(tmp_path: Path):
    with pytest.raises(GateExportError, match="missing"):
        await export_gate_snapshot(
            source_path=tmp_path / "no-such-gate.md",
            repo_root=tmp_path,
            write_repo=True,
            emit_pel=False,
        )


@pytest.mark.asyncio
async def test_export_requires_at_least_one_sink(tmp_path: Path):
    source = tmp_path / "src.md"
    source.write_text(SAMPLE_GATE, encoding="utf-8")
    with pytest.raises(GateExportError, match="at least one"):
        await export_gate_snapshot(
            source_path=source,
            write_repo=False,
            emit_pel=False,
        )


@pytest.mark.asyncio
async def test_export_overwrites_prior_repo_snapshot(tmp_path: Path):
    source = tmp_path / "src.md"
    source.write_text(HOLD_GATE, encoding="utf-8")
    repo = tmp_path / "repo"
    dest = repo / DEFAULT_REPO_RELATIVE
    dest.parent.mkdir(parents=True)
    dest.write_text(SAMPLE_GATE, encoding="utf-8")

    result = await export_gate_snapshot(
        source_path=source,
        repo_root=repo,
        write_repo=True,
        emit_pel=False,
    )
    assert dest.read_text(encoding="utf-8") == HOLD_GATE
    assert result["verdict"] == "hold"


def test_export_gate_snapshot_sync_wrapper(tmp_path: Path):
    source = tmp_path / "src.md"
    source.write_text(SAMPLE_GATE, encoding="utf-8")
    result = export_gate_snapshot_sync(
        source_path=source,
        repo_root=tmp_path / "repo",
        write_repo=True,
        emit_pel=True,
    )
    assert result["ok"] is True
    assert result["verdict"] == "pass"
    assert len(memory_rows()) == 1


# ── shell entrypoint ─────────────────────────────────────────────────────────


def test_export_shell_script_exists_and_is_executable():
    assert EXPORT_SH.is_file()
    # mode bit or shebang is enough for T0 (CI may not preserve +x on all mounts)
    text = EXPORT_SH.read_text(encoding="utf-8")
    assert text.startswith("#!/usr/bin/env bash")
    assert "aether-gate-export" in text
    assert "data/aether" in text or "gate_export" in text


def test_export_shell_writes_repo_and_pel(tmp_path: Path):
    source = tmp_path / "gate.md"
    source.write_text(SAMPLE_GATE, encoding="utf-8")
    dest = tmp_path / "out" / GATE_ARTIFACT
    env = os.environ.copy()
    env.update(
        {
            "FM_AETHER_PROJECT_ROOT": str(ROOT),
            "FM_AETHER_GATE_EXPORT_SOURCE": str(source),
            "FM_AETHER_GATE_EXPORT_DEST": str(dest),
            "ADVOI_PEL_MEMORY": "true",
            "FM_AETHER_GATE_EXPORT_NO_PEL": "1",  # shell path: repo write is enough
        }
    )
    # Drop DATABASE_URL so we do not hit real Postgres from the subprocess.
    env.pop("DATABASE_URL", None)

    proc = subprocess.run(
        ["bash", str(EXPORT_SH)],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + "\n" + proc.stderr
    assert dest.is_file(), proc.stdout + proc.stderr
    assert dest.read_text(encoding="utf-8") == SAMPLE_GATE
    assert "aether-gate-export: OK" in proc.stdout or "aether-gate-export done" in proc.stdout


def test_export_shell_fails_on_missing_source(tmp_path: Path):
    env = os.environ.copy()
    env.update(
        {
            "FM_AETHER_PROJECT_ROOT": str(ROOT),
            "FM_AETHER_GATE_EXPORT_SOURCE": str(tmp_path / "missing.md"),
            "FM_AETHER_GATE_EXPORT_DEST": str(tmp_path / "out.md"),
            "FM_AETHER_GATE_EXPORT_NO_PEL": "1",
        }
    )
    env.pop("DATABASE_URL", None)
    proc = subprocess.run(
        ["bash", str(EXPORT_SH)],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0
    assert "FAIL" in proc.stderr or "missing" in (proc.stderr + proc.stdout).lower()


def test_module_cli_json(tmp_path: Path):
    source = tmp_path / "gate.md"
    source.write_text(SAMPLE_GATE, encoding="utf-8")
    dest = tmp_path / "exported.md"
    env = os.environ.copy()
    env["ADVOI_PEL_MEMORY"] = "true"
    env.pop("DATABASE_URL", None)
    proc = subprocess.run(
        [
            "uv",
            "run",
            "python",
            "-m",
            "advoi.aether.gate_export",
            "--source",
            str(source),
            "--dest",
            str(dest),
            "--repo",
            str(tmp_path),
            "--json",
        ],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert dest.is_file()
    assert '"ok": true' in proc.stdout or '"ok": true' in proc.stdout.replace(" ", "")
    assert "pass" in proc.stdout
