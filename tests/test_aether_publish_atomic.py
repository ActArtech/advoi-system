"""T0: atomic publish of gate + proactive + directives to fleet tree.

Success writes all three; failure leaves prior artifacts intact.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.bash_util import bash_available, run_bash

from advoi.aether.publish_atomic import (
    ARTIFACT_NAMES,
    DIRECTIVES_ARTIFACT,
    GATE_ARTIFACT,
    PROACTIVE_ARTIFACT,
    PublishError,
    build_artifact_map,
    publish_atomic,
    publish_from_paths,
    read_sources,
)

ROOT = Path(__file__).resolve().parents[1]
PUBLISH_SH = ROOT / "scripts" / "aether-publish-atomic.sh"

OLD_GATE = "# Aether output gate — OLD\n\n**Verdict:** pass\n**Active slug:** advoi\n"
NEW_GATE = "# Aether output gate — NEW\n\n**Verdict:** hold\n**Active slug:** advoi\n"
OLD_PROACTIVE = (
    '{\n  "project": "/data/projects/advoi",\n  "mode": "proactive",\n'
    '  "findings": [{"agent": "context", "severity": "none",'
    ' "category": "audit", "message": "old cycle"}]\n}\n'
)
NEW_PROACTIVE = (
    '{\n  "project": "/data/projects/advoi",\n  "mode": "proactive",\n'
    '  "findings": [{"agent": "context", "severity": "none",'
    ' "category": "audit", "message": "new cycle"}]\n}\n'
)
OLD_DIRECTIVES = (
    "# Aether directives (proactive)\n\nGenerated **2026-01-01 00:00 UTC**\n\n"
    "## Findings\n\n- old\n\n| Top finding | old |\n\nadvoi\n"
)
NEW_DIRECTIVES = (
    "# Aether directives (proactive)\n\nGenerated **2026-07-10 12:00 UTC**\n\n"
    "## Findings\n\n- new\n\n| Top finding | new |\n\nadvoi\n"
)


def _seed_prior(fleet: Path) -> None:
    fleet.mkdir(parents=True, exist_ok=True)
    (fleet / GATE_ARTIFACT).write_text(OLD_GATE, encoding="utf-8")
    (fleet / PROACTIVE_ARTIFACT).write_text(OLD_PROACTIVE, encoding="utf-8")
    (fleet / DIRECTIVES_ARTIFACT).write_text(OLD_DIRECTIVES, encoding="utf-8")


def _new_map() -> dict[str, str]:
    return build_artifact_map(
        gate_text=NEW_GATE,
        proactive_text=NEW_PROACTIVE,
        directives_text=NEW_DIRECTIVES,
    )


def _assert_prior_intact(fleet: Path) -> None:
    assert (fleet / GATE_ARTIFACT).read_text(encoding="utf-8") == OLD_GATE
    assert (fleet / PROACTIVE_ARTIFACT).read_text(encoding="utf-8") == OLD_PROACTIVE
    assert (fleet / DIRECTIVES_ARTIFACT).read_text(encoding="utf-8") == OLD_DIRECTIVES


def _assert_new_written(fleet: Path) -> None:
    assert (fleet / GATE_ARTIFACT).read_text(encoding="utf-8") == NEW_GATE
    assert (fleet / PROACTIVE_ARTIFACT).read_text(encoding="utf-8") == NEW_PROACTIVE
    assert (fleet / DIRECTIVES_ARTIFACT).read_text(encoding="utf-8") == NEW_DIRECTIVES


# ── pure helpers ─────────────────────────────────────────────────────────────


def test_artifact_names_are_the_three_canonical_files():
    assert ARTIFACT_NAMES == (
        "aether-gate-latest.md",
        "aether-proactive-latest.json",
        "AETHER-DIRECTIVES.md",
    )


def test_build_artifact_map_rejects_empty():
    with pytest.raises(PublishError, match="empty"):
        build_artifact_map(gate_text="x", proactive_text="y", directives_text="  ")


def test_read_sources_missing_raises(tmp_path: Path):
    with pytest.raises(PublishError, match="missing"):
        read_sources(
            gate_path=tmp_path / "no-gate.md",
            proactive_path=tmp_path / "no.json",
            directives_path=tmp_path / "no.md",
        )


# ── success: all three written ───────────────────────────────────────────────


def test_publish_atomic_success_writes_all_three(tmp_path: Path):
    fleet = tmp_path / "fleet"
    result = publish_atomic(fleet, _new_map())
    _assert_new_written(fleet)
    assert set(result["artifacts"]) >= set(ARTIFACT_NAMES)
    assert result["committed"] == list(result["artifacts"])
    # No leftover staging/backup dirs
    leftovers = [p.name for p in fleet.iterdir() if p.name.startswith(".aether-publish-")]
    assert leftovers == []


def test_publish_atomic_overwrites_prior(tmp_path: Path):
    fleet = tmp_path / "fleet"
    _seed_prior(fleet)
    publish_atomic(fleet, _new_map())
    _assert_new_written(fleet)


def test_publish_from_paths_success(tmp_path: Path):
    src = tmp_path / "src"
    fleet = tmp_path / "fleet"
    src.mkdir()
    gate = src / "gate.md"
    proactive = src / "proactive.json"
    directives = src / "directives.md"
    gate.write_text(NEW_GATE, encoding="utf-8")
    proactive.write_text(NEW_PROACTIVE, encoding="utf-8")
    directives.write_text(NEW_DIRECTIVES, encoding="utf-8")

    publish_from_paths(
        dest_dir=fleet,
        gate_path=gate,
        proactive_path=proactive,
        directives_path=directives,
    )
    _assert_new_written(fleet)


# ── failure: prior artifacts intact ──────────────────────────────────────────


def test_publish_failure_after_stage_leaves_prior_intact(tmp_path: Path):
    fleet = tmp_path / "fleet"
    _seed_prior(fleet)
    with pytest.raises(PublishError, match="injected failure after stage"):
        publish_atomic(fleet, _new_map(), _fail_after_stage=True)
    _assert_prior_intact(fleet)
    leftovers = [p.name for p in fleet.iterdir() if p.name.startswith(".aether-publish-")]
    assert leftovers == []


def test_publish_failure_mid_commit_restores_prior(tmp_path: Path):
    """If replace fails after the first file, restore all prior content."""
    fleet = tmp_path / "fleet"
    _seed_prior(fleet)
    with pytest.raises(PublishError, match="injected mid-commit"):
        publish_atomic(fleet, _new_map(), _fail_mid_commit_after=1)
    _assert_prior_intact(fleet)


def test_publish_missing_source_leaves_prior_intact(tmp_path: Path):
    fleet = tmp_path / "fleet"
    _seed_prior(fleet)
    src = tmp_path / "src"
    src.mkdir()
    (src / "gate.md").write_text(NEW_GATE, encoding="utf-8")
    # proactive intentionally missing
    (src / "directives.md").write_text(NEW_DIRECTIVES, encoding="utf-8")
    with pytest.raises(PublishError, match="missing"):
        publish_from_paths(
            dest_dir=fleet,
            gate_path=src / "gate.md",
            proactive_path=src / "proactive.json",
            directives_path=src / "directives.md",
        )
    _assert_prior_intact(fleet)


def test_publish_empty_artifact_rejected_leaves_prior(tmp_path: Path):
    fleet = tmp_path / "fleet"
    _seed_prior(fleet)
    bad = dict(_new_map())
    bad[GATE_ARTIFACT] = ""
    with pytest.raises(PublishError, match="empty"):
        publish_atomic(fleet, bad)
    _assert_prior_intact(fleet)


# ── shell entrypoint ─────────────────────────────────────────────────────────


def test_publish_script_exists_and_documents_atomic():
    assert PUBLISH_SH.is_file()
    text = PUBLISH_SH.read_text(encoding="utf-8")
    assert text.startswith("#!/usr/bin/env bash")
    assert "all-or-nothing" in text or "atomically" in text.lower() or "atomic" in text
    assert GATE_ARTIFACT in text
    assert PROACTIVE_ARTIFACT in text
    assert DIRECTIVES_ARTIFACT in text


def _run_publish_sh(
    *,
    fleet: Path,
    gate: Path,
    proactive: Path,
    directives: Path,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["FM_AETHER_PUBLISH_DEST"] = str(fleet)
    env["FM_AETHER_GATE_REPORT"] = str(gate)
    env["FM_AETHER_PROACTIVE"] = str(proactive)
    env["FM_AETHER_DIRECTIVES"] = str(directives)
    env["FM_AETHER_PROJECT_ROOT"] = str(ROOT)
    return run_bash(
        PUBLISH_SH,
        capture_output=True,
        text=True,
        check=False,
        cwd=str(ROOT),
        env=env,
    )


@pytest.mark.skipif(not bash_available(), reason="bash not available")
def test_shell_success_writes_all_three(tmp_path: Path):
    fleet = tmp_path / "fleet"
    src = tmp_path / "src"
    src.mkdir()
    gate = src / "gate.md"
    proactive = src / "pro.json"
    directives = src / "dir.md"
    gate.write_text(NEW_GATE, encoding="utf-8")
    proactive.write_text(NEW_PROACTIVE, encoding="utf-8")
    directives.write_text(NEW_DIRECTIVES, encoding="utf-8")

    proc = _run_publish_sh(
        fleet=fleet, gate=gate, proactive=proactive, directives=directives
    )
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0, out
    assert "aether-publish: OK" in out
    _assert_new_written(fleet)


@pytest.mark.skipif(not bash_available(), reason="bash not available")
def test_shell_failure_missing_source_leaves_prior(tmp_path: Path):
    fleet = tmp_path / "fleet"
    _seed_prior(fleet)
    src = tmp_path / "src"
    src.mkdir()
    gate = src / "gate.md"
    proactive = src / "pro.json"  # not created
    directives = src / "dir.md"
    gate.write_text(NEW_GATE, encoding="utf-8")
    directives.write_text(NEW_DIRECTIVES, encoding="utf-8")

    proc = _run_publish_sh(
        fleet=fleet, gate=gate, proactive=proactive, directives=directives
    )
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, out
    assert "missing" in out.lower() or "ERROR" in out
    _assert_prior_intact(fleet)


def test_cli_module_main_success(tmp_path: Path):
    src = tmp_path / "src"
    fleet = tmp_path / "fleet"
    src.mkdir()
    gate = src / "g.md"
    proactive = src / "p.json"
    directives = src / "d.md"
    gate.write_text(NEW_GATE, encoding="utf-8")
    proactive.write_text(NEW_PROACTIVE, encoding="utf-8")
    directives.write_text(NEW_DIRECTIVES, encoding="utf-8")

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "advoi.aether.publish_atomic",
            "--fleet",
            str(fleet),
            "--gate",
            str(gate),
            "--proactive",
            str(proactive),
            "--directives",
            str(directives),
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(ROOT),
        env={**os.environ, "PYTHONPATH": str(ROOT)},
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    _assert_new_written(fleet)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
