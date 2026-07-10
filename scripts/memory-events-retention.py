#!/usr/bin/env python3
"""Age-prune legacy Postgres ``memory_events`` rows (retention job).

Safe defaults:
  - dry-run unless ``--apply`` is passed
  - 90-day window (floor 7) via ``ADVOI_MEMORY_EVENTS_RETENTION_DAYS``

Does **not** delete ``portfolio_events`` (PEL), briefs, or review_queue.

Usage:
  # Count rows older than retention (no delete)
  python scripts/memory-events-retention.py
  python scripts/memory-events-retention.py --dry-run

  # Delete (requires explicit apply)
  python scripts/memory-events-retention.py --apply
  python scripts/memory-events-retention.py --apply --days 120

  # Cron example (weekly, dry-run first then apply once trusted):
  # 20 3 * * 0 cd /opt/advoi && \\
  #   python scripts/memory-events-retention.py --apply \\
  #   >> /var/log/advoi-memory-events-retention.log 2>&1

Env:
  DATABASE_URL
  ADVOI_MEMORY_EVENTS_RETENTION_DAYS   default 90
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

# Allow ``python scripts/memory-events-retention.py`` from repo root.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _load_dotenv() -> None:
    env_file = os.getenv("ENV_FILE", str(_ROOT / "deploy" / ".env"))
    path = Path(env_file)
    if not path.is_file():
        return
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip("'").strip('"')
            if key and key not in os.environ:
                os.environ[key] = val
    except OSError:
        pass


async def _run(args: argparse.Namespace) -> int:
    from advoi.memory.postgres_store import (
        MIN_MEMORY_EVENTS_RETENTION_DAYS,
        prune_memory_events,
    )

    days = args.days
    dry_run = not args.apply
    if days is not None and days < MIN_MEMORY_EVENTS_RETENTION_DAYS:
        print(
            f"ERROR: --days must be >= {MIN_MEMORY_EVENTS_RETENTION_DAYS} "
            f"(got {days})",
            file=sys.stderr,
        )
        return 2

    result = await prune_memory_events(retention_days=days, dry_run=dry_run)
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result.get("ok"):
        return 1
    mode = "dry-run" if dry_run else "apply"
    print(
        f"memory_events retention ({mode}): "
        f"matched={result.get('matched', 0)} deleted={result.get('deleted', 0)} "
        f"cutoff={result.get('cutoff')} days={result.get('retention_days')}",
        file=sys.stderr,
    )
    return 0


def main() -> None:
    _load_dotenv()
    parser = argparse.ArgumentParser(
        description="Prune legacy memory_events older than retention window",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help=(
            "Retention days (default: ADVOI_MEMORY_EVENTS_RETENTION_DAYS or 90; "
            f"floor {7})"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Count only (default when --apply is omitted)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Actually DELETE rows older than the cutoff (off by default)",
    )
    args = parser.parse_args()
    if args.dry_run and args.apply:
        print("ERROR: pass only one of --dry-run / --apply", file=sys.stderr)
        sys.exit(2)
    raise SystemExit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()
