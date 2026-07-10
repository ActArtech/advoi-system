#!/usr/bin/env python3
"""Seed open briefs locally — Postgres canonical, Redis cache fill only (ADR-026)."""
from __future__ import annotations

import asyncio
import os
import sys

BRIEFS = [
    "ADVoi voice launch: validate PWA connect, frame buttons, and TTS on staging",
    "Shelve secrets: push fixed OPENAI_API_KEY to ktteam/advoi/staging",
    "Portfolio registration: add advoi row to vps-shared port registry",
]


async def seed_postgres() -> bool:
    try:
        from advoi.memory.postgres_store import upsert_open_brief

        ok = True
        for b in BRIEFS:
            # upsert_open_brief invalidates Redis advoi:briefs:open after each write
            if not await upsert_open_brief(b):
                ok = False
        return ok
    except Exception as e:
        print(f"WARN Postgres: {e}", file=sys.stderr)
        return False


def seed_redis_cache() -> bool:
    """Fill Redis from the same canonical list (cache of PG, not a merge source)."""
    try:
        from advoi.memory.briefs_cache import fill_open_briefs_cache

        return fill_open_briefs_cache(BRIEFS)
    except Exception as e:
        print(f"WARN Redis: {e}", file=sys.stderr)
        return False


async def main() -> int:
    pg = await seed_postgres()
    # Fill cache after PG writes (writes invalidate; fill restores mirror of seed titles).
    rd = seed_redis_cache()
    if pg:
        print("OK: Postgres briefs (canonical)")
    if rd:
        print("OK: Redis briefs cache filled")
    return 0 if (pg or rd) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
