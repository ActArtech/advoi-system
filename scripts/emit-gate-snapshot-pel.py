#!/usr/bin/env python3
"""Emit gate_snapshot rows to portfolio_events after fm-aether-gate PASS."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from advoi.portfolio.gate_snapshot import emit_gate_snapshot_from_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report_path", help="Path to aether-gate-latest.md")
    parser.add_argument("exit_code", type=int, help="fm-aether-gate exit code")
    args = parser.parse_args(argv)

    report_path = Path(args.report_path)
    if not report_path.is_file():
        print(f"PEL_GATE_SNAPSHOT_SKIP: missing report {report_path}", file=sys.stderr)
        return 0

    ok = asyncio.run(emit_gate_snapshot_from_report(str(report_path), args.exit_code))
    if ok:
        print("PEL_GATE_SNAPSHOT_OK")
        return 0
    print("PEL_GATE_SNAPSHOT_SKIP: DATABASE_URL unset or append failed", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())