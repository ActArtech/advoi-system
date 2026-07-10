"""T0: FM_AETHER_GATE_REQUIRED=1 skips fleet feed when gate exit >= 2."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from advoi.aether.feed_cron import (
    GATE_FAIL,
    GATE_PASS,
    GATE_PASS_AUDIT_ONLY,
    feed_decision,
    is_gate_required,
    should_skip_feed,
    skip_log_line,
)

ROOT = Path(__file__).resolve().parents[1]
CRON_SH = ROOT / "scripts" / "aether-feed-cron.sh"


# ── pure decision ────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "value,expected",
    [
        ("1", True),
        (1, True),
        (True, True),
        ("true", True),
        ("yes", True),
        ("on", True),
        ("0", False),
        (0, False),
        (False, False),
        ("", False),
        (None, False),
        ("false", False),
    ],
)
def test_is_gate_required(value, expected):
    assert is_gate_required(value) is expected


@pytest.mark.parametrize(
    "gate_required,gate_exit,skip",
    [
        (True, GATE_FAIL, True),
        (True, 3, True),
        (True, GATE_PASS, False),
        (True, GATE_PASS_AUDIT_ONLY, False),
        (False, GATE_FAIL, False),
        ("0", GATE_FAIL, False),
        ("1", GATE_FAIL, True),
        ("1", GATE_PASS_AUDIT_ONLY, False),
        ("1", GATE_PASS, False),
    ],
)
def test_should_skip_feed(gate_required, gate_exit, skip):
    assert should_skip_feed(gate_required=gate_required, gate_exit=gate_exit) is skip


def test_skip_log_line_mentions_fail_and_env():
    line = skip_log_line(2)
    assert "aether-feed: skipped — gate FAIL" in line
    assert "exit=2" in line
    assert "FM_AETHER_GATE_REQUIRED=1" in line


def test_feed_decision_skip_includes_log():
    d = feed_decision(gate_required="1", gate_exit=2)
    assert d["action"] == "skip"
    assert d["reason"] == "gate_fail"
    assert d["log"] == skip_log_line(2)


def test_feed_decision_publish_pass_and_audit_only():
    for code in (GATE_PASS, GATE_PASS_AUDIT_ONLY):
        d = feed_decision(gate_required=1, gate_exit=code)
        assert d["action"] == "publish"
        assert d["log"] is None


def test_feed_decision_publish_when_not_required_even_on_fail():
    d = feed_decision(gate_required=0, gate_exit=GATE_FAIL)
    assert d["action"] == "publish"
    assert d["reason"] == "gate_not_required"


# ── shell cron with mocked gate exit codes ───────────────────────────────────


def _run_cron(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    base = os.environ.copy()
    base.update(env)
    # Isolate from real firstmate scripts
    base.setdefault("FM_AETHER_FEED_CMD", "echo FEED_RAN")
    return subprocess.run(
        ["bash", str(CRON_SH)],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(ROOT),
        env=base,
    )


def test_cron_script_exists_and_is_executable_bit_or_bashable():
    assert CRON_SH.is_file()
    # Shebang present even if mode not +x in tree
    text = CRON_SH.read_text(encoding="utf-8")
    assert text.startswith("#!/usr/bin/env bash")
    assert "FM_AETHER_GATE_REQUIRED" in text


def test_cron_skips_feed_when_gate_exit_2_and_required():
    proc = _run_cron(
        {
            "FM_AETHER_GATE_REQUIRED": "1",
            "FM_AETHER_GATE_EXIT": "2",
            "FM_AETHER_FEED_CMD": "echo FEED_RAN",
        }
    )
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0, out
    assert "aether-feed: skipped — gate FAIL (exit=2) [FM_AETHER_GATE_REQUIRED=1]" in out
    assert "FEED_RAN" not in out


def test_cron_skips_feed_when_gate_exit_3_and_required():
    proc = _run_cron(
        {
            "FM_AETHER_GATE_REQUIRED": "1",
            "FM_AETHER_GATE_EXIT": "3",
            "FM_AETHER_FEED_CMD": "echo FEED_RAN",
        }
    )
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0, out
    assert "aether-feed: skipped — gate FAIL (exit=3)" in out
    assert "FEED_RAN" not in out


def test_cron_publishes_on_gate_pass_exit_0():
    proc = _run_cron(
        {
            "FM_AETHER_GATE_REQUIRED": "1",
            "FM_AETHER_GATE_EXIT": "0",
            "FM_AETHER_FEED_CMD": "echo FEED_RAN",
        }
    )
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0, out
    assert "FEED_RAN" in out
    assert "aether-feed: skipped" not in out


def test_cron_publishes_on_gate_pass_audit_only_exit_1():
    proc = _run_cron(
        {
            "FM_AETHER_GATE_REQUIRED": "1",
            "FM_AETHER_GATE_EXIT": "1",
            "FM_AETHER_FEED_CMD": "echo FEED_RAN",
        }
    )
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0, out
    assert "FEED_RAN" in out
    assert "PASS_AUDIT_ONLY" in out
    assert "aether-feed: skipped" not in out


def test_cron_publishes_when_gate_not_required_even_on_fail():
    proc = _run_cron(
        {
            "FM_AETHER_GATE_REQUIRED": "0",
            "FM_AETHER_GATE_EXIT": "2",
            "FM_AETHER_FEED_CMD": "echo FEED_RAN",
        }
    )
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0, out
    assert "FEED_RAN" in out
    assert "aether-feed: skipped" not in out


def test_cron_gate_cmd_mock_exit_2_skips():
    """Mock via FM_AETHER_GATE_CMD (shell snippet) instead of FM_AETHER_GATE_EXIT."""
    proc = _run_cron(
        {
            "FM_AETHER_GATE_REQUIRED": "1",
            "FM_AETHER_GATE_CMD": "exit 2",
            "FM_AETHER_FEED_CMD": "echo FEED_RAN",
        }
    )
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0, out
    assert "aether-feed: skipped — gate FAIL (exit=2) [FM_AETHER_GATE_REQUIRED=1]" in out
    assert "FEED_RAN" not in out


def test_cron_defaults_gate_required_to_one():
    """Omitting FM_AETHER_GATE_REQUIRED still defaults to required=1."""
    env = {
        "FM_AETHER_GATE_EXIT": "2",
        "FM_AETHER_FEED_CMD": "echo FEED_RAN",
    }
    # Explicitly drop if inherited
    base = os.environ.copy()
    base.pop("FM_AETHER_GATE_REQUIRED", None)
    base.update(env)
    proc = subprocess.run(
        ["bash", str(CRON_SH)],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(ROOT),
        env=base,
    )
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0, out
    assert "aether-feed: skipped — gate FAIL" in out
    assert "FEED_RAN" not in out


def test_python_and_shell_skip_line_match():
    """Keep shell log string in sync with feed_cron.skip_log_line."""
    expected = skip_log_line(2)
    text = CRON_SH.read_text(encoding="utf-8")
    # Shell uses ${gate_rc}; verify template shape
    assert "aether-feed: skipped — gate FAIL (exit=${gate_rc}) [FM_AETHER_GATE_REQUIRED=1]" in text
    assert expected == "aether-feed: skipped — gate FAIL (exit=2) [FM_AETHER_GATE_REQUIRED=1]"


if __name__ == "__main__":
    # Allow quick manual run without pytest discovery path issues
    sys.exit(pytest.main([__file__, "-q"]))
