"""T0 tests for T2 staging smoke validators and fixture-mode script."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
VALIDATE = ROOT / "scripts" / "t2_validate.py"
SMOKE_SH = ROOT / "scripts" / "t2-staging-smoke.sh"
FIXTURES = ROOT / "tests" / "fixtures" / "t2-smoke"
FIXTURES_BAD = ROOT / "tests" / "fixtures" / "t2-smoke-bad"

# Import pure validators without installing the package path hacks.
sys.path.insert(0, str(ROOT / "scripts"))
from t2_validate import validate_aether_status, validate_health  # noqa: E402


def _load(name: str, *, bad: bool = False) -> dict:
    base = FIXTURES_BAD if bad else FIXTURES
    return json.loads((base / name).read_text(encoding="utf-8"))


def test_validate_health_ok():
    errors = validate_health(_load("health.json"))
    assert errors == []


def test_validate_health_requires_six_agents():
    data = _load("health.json")
    data["agents_ready"] = 5
    data["agents_total"] = 6
    errors = validate_health(data)
    assert any("agents_ready" in e for e in errors)

    data["agents_ready"] = 6
    data["agents_total"] = 5
    errors = validate_health(data)
    assert any("agents_total" in e for e in errors)


def test_validate_health_rejects_ok_false():
    data = _load("health.json")
    data["ok"] = False
    errors = validate_health(data)
    assert any("ok=" in e for e in errors)


def test_validate_health_custom_expected_agents():
    data = {
        "ok": True,
        "service": "advoi-api",
        "agents_ready": 3,
        "agents_total": 3,
    }
    assert validate_health(data, expected_agents=3) == []
    assert validate_health(data, expected_agents=6)  # non-empty errors


def test_validate_aether_status_ok():
    errors = validate_aether_status(_load("aether-status.json"))
    assert errors == []


def test_validate_aether_status_missing_keys():
    errors = validate_aether_status(_load("aether-status.json", bad=True))
    assert any("frame_coverage" in e for e in errors)
    assert any("memory" in e for e in errors)


def test_validate_aether_status_memory_letta_health():
    data = _load("aether-status.json")
    data["memory"] = {"letta_enabled": False}
    errors = validate_aether_status(data)
    assert any("letta_health" in e for e in errors)


def test_cli_validate_health_fixture():
    proc = subprocess.run(
        [sys.executable, str(VALIDATE), "health", str(FIXTURES / "health.json")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "OK: health" in proc.stdout


def test_cli_validate_health_bad_fixture_fails():
    proc = subprocess.run(
        [sys.executable, str(VALIDATE), "health", str(FIXTURES_BAD / "health.json")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    assert "FAIL:" in proc.stderr


def test_cli_validate_aether_fixture():
    proc = subprocess.run(
        [sys.executable, str(VALIDATE), "aether", str(FIXTURES / "aether-status.json")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr


def test_smoke_script_fixture_mode_passes():
    proc = subprocess.run(
        ["bash", str(SMOKE_SH), "--fixture-dir", str(FIXTURES)],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(ROOT),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "T2 staging smoke PASSED" in proc.stdout


def test_smoke_script_fixture_mode_fails_on_bad_agents():
    proc = subprocess.run(
        ["bash", str(SMOKE_SH), "--fixture-dir", str(FIXTURES_BAD)],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(ROOT),
    )
    assert proc.returncode == 1
    assert "FAILED" in (proc.stdout + proc.stderr)


def test_smoke_script_missing_fixture_dir_fails():
    missing = ROOT / "tests" / "fixtures" / "t2-smoke-missing"
    proc = subprocess.run(
        ["bash", str(SMOKE_SH), "--fixture-dir", str(missing)],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(ROOT),
    )
    assert proc.returncode == 1
