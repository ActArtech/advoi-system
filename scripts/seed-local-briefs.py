#!/usr/bin/env python3
from __future__ import annotations
import asyncio, json, os, sys
BRIEFS = [
    "Open brief: ADVoi voice launch, validate PWA connect, frame buttons, and TTS on staging",
    "Open brief: Shelve secrets, push fixed OPENAI_API_KEY to ktteam/advoi/staging",
    "Open brief: Portfolio registration, add advoi row to vps-shared port registry",
]
async def seed_postgres():
    try:
        from advoi.memory.postgres_store import upsert_open_brief
        for b in BRIEFS: await upsert_open_brief(b)
        return True
    except Exception as e:
        print(f"WARN Postgres: {e}", file=sys.stderr); return False
def seed_redis():
    try:
        import redis
        c = redis.from_url(os.getenv("REDIS_URL", "redis://127.0.0.1:6382/0"), decode_responses=True)
        c.set("advoi:briefs:open", json.dumps(BRIEFS)); return True
    except Exception as e:
        print(f"WARN Redis: {e}", file=sys.stderr); return False
async def main():
    pg, rd = await seed_postgres(), seed_redis()
    if pg: print("OK: Postgres briefs")
    if rd: print("OK: Redis briefs")
    return 0 if (pg or rd) else 1
if __name__ == "__main__": raise SystemExit(asyncio.run(main()))