#!/usr/bin/env python3
"""T2 staging smoke response validators.

Used by scripts/t2-staging-smoke.sh and tests/test_t2_staging_smoke.py.
Pure functions — no network I/O.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

DEFAULT_EXPECTED_AGENTS = 6


def validate_health(
    data: dict[str, Any],
    *,
    expected_agents: int = DEFAULT_EXPECTED_AGENTS,
) -> list[str]:
    """Return a list of error strings (empty = pass)."""
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["health: response is not a JSON object"]

    if data.get("ok") is not True:
        errors.append(f"health: ok={data.get('ok')!r}, expected true")

    total = data.get("agents_total")
    ready = data.get("agents_ready")
    if total != expected_agents:
        errors.append(f"health: agents_total={total!r}, expected {expected_agents}")
    if ready != expected_agents:
        errors.append(f"health: agents_ready={ready!r}, expected {expected_agents}")
    if data.get("service") != "advoi-api":
        errors.append(f"health: service={data.get('service')!r}, expected 'advoi-api'")
    return errors


def validate_aether_status(data: dict[str, Any]) -> list[str]:
    """Return a list of error strings (empty = pass)."""
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["aether/status: response is not a JSON object"]

    if "gate" not in data:
        errors.append("aether/status: missing 'gate'")
    if "frame_coverage" not in data:
        errors.append("aether/status: missing 'frame_coverage'")
    if "memory" not in data:
        errors.append("aether/status: missing 'memory'")
    else:
        memory = data["memory"]
        if not isinstance(memory, dict):
            errors.append("aether/status: memory is not an object")
        elif "letta_health" not in memory:
            errors.append("aether/status: memory.letta_health missing")

    # Active venture may be null on a cold stack, but key should exist when
    # portfolio is loaded. Prefer presence of portfolio_total as readiness signal.
    if "portfolio_total" not in data and "active_venture" not in data:
        errors.append("aether/status: missing portfolio_total and active_venture")
    return errors


def _load_json(path: str) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate T2 smoke JSON fixtures")
    parser.add_argument(
        "kind",
        choices=("health", "aether"),
        help="Which response shape to validate",
    )
    parser.add_argument(
        "path",
        nargs="?",
        help="JSON file path (default: stdin)",
    )
    parser.add_argument(
        "--expected-agents",
        type=int,
        default=DEFAULT_EXPECTED_AGENTS,
        help=f"Expected agents_ready/agents_total (default {DEFAULT_EXPECTED_AGENTS})",
    )
    args = parser.parse_args(argv)

    raw = _load_json(args.path) if args.path else json.load(sys.stdin)
    if args.kind == "health":
        errors = validate_health(raw, expected_agents=args.expected_agents)
    else:
        errors = validate_aether_status(raw)

    if errors:
        for err in errors:
            print(f"FAIL: {err}", file=sys.stderr)
        return 1
    print(f"OK: {args.kind}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
