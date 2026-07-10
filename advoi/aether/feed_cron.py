"""Fleet feed cron helpers — gate-required skip policy.

When ``FM_AETHER_GATE_REQUIRED=1``, feed publish must not run if the Aether
gate exits with code >= 2 (FAIL). Exit 0 (PASS) and 1 (PASS_AUDIT_ONLY) allow
feed to proceed.

Used by ``scripts/aether-feed-cron.sh`` and T0 tests with mocked gate codes.
"""

from __future__ import annotations

from typing import Any

# Gate exit codes (must match /opt/firstmate/scripts/fm-aether-gate.sh).
GATE_PASS = 0
GATE_PASS_AUDIT_ONLY = 1
GATE_FAIL = 2

SKIP_LOG_PREFIX = "aether-feed: skipped — gate FAIL"


def is_gate_required(value: Any) -> bool:
    """True when FM_AETHER_GATE_REQUIRED is enabled (1/true/yes/on)."""
    if value is True:
        return True
    if value is False or value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def should_skip_feed(*, gate_required: Any, gate_exit: int) -> bool:
    """Return True when feed publish must be skipped for a FAIL gate."""
    if not is_gate_required(gate_required):
        return False
    return int(gate_exit) >= GATE_FAIL


def skip_log_line(gate_exit: int) -> str:
    """Canonical log line when feed is skipped due to FAIL gate."""
    return (
        f"{SKIP_LOG_PREFIX} (exit={int(gate_exit)}) "
        f"[FM_AETHER_GATE_REQUIRED=1]"
    )


def feed_decision(*, gate_required: Any, gate_exit: int) -> dict[str, Any]:
    """Structured decision for cron / tests.

    Returns:
        action: ``skip`` | ``publish``
        reason: short machine-readable reason
        log: optional log line (only when skip due to FAIL gate)
    """
    required = is_gate_required(gate_required)
    exit_code = int(gate_exit)
    if should_skip_feed(gate_required=required, gate_exit=exit_code):
        return {
            "action": "skip",
            "reason": "gate_fail",
            "gate_required": True,
            "gate_exit": exit_code,
            "log": skip_log_line(exit_code),
        }
    return {
        "action": "publish",
        "reason": "gate_ok" if required else "gate_not_required",
        "gate_required": required,
        "gate_exit": exit_code,
        "log": None,
    }
