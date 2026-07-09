"""Lightweight diagnostics probes for specialist agent frames."""

from __future__ import annotations

import os
import time
from typing import Any

import httpx

from advoi.cache.agent_cache import agents_status_summary
from advoi.memory.router import load_memory_config
from advoi.routing.intent import resolve_voice_action


async def probe_memory_bridge() -> dict[str, Any]:
    url = os.getenv("HINDSIGHT_BRIDGE_URL", "").rstrip("/")
    if not url:
        return {"memory_bridge_ok": False, "memory_bridge_mode": "mock"}
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(2.0, connect=1.0)) as client:
            resp = await client.get(f"{url}/health")
            resp.raise_for_status()
            return {"memory_bridge_ok": True, "memory_bridge_mode": "hermes"}
    except Exception:
        return {"memory_bridge_ok": False, "memory_bridge_mode": "unavailable"}


async def memory_health_snapshot() -> dict[str, Any]:
    cfg = load_memory_config()
    bridge = await probe_memory_bridge()
    store_path = os.getenv("ADVOI_OPERATIONAL_STORE", "data/operational-memory.jsonl")
    return {
        "provider": cfg.provider,
        "hindsight_enabled": cfg.hindsight_enabled,
        "letta_enabled": cfg.letta_enabled,
        "redis_configured": bool(cfg.redis_url),
        "postgres_configured": bool(cfg.database_url),
        "operational_store_exists": os.path.isfile(store_path),
        **bridge,
    }


async def quick_latency_ms() -> dict[str, Any]:
    sla_ms = float(os.getenv("ADVOI_LATENCY_SLA_MS", "800"))
    started = time.perf_counter()
    resolve_voice_action("fleet status please")
    intent_ms = round((time.perf_counter() - started) * 1000, 1)
    started = time.perf_counter()
    from advoi.routing.frame_runner import run_frame

    await run_frame("fleet_status", use_cache=True)
    frame_ms = round((time.perf_counter() - started) * 1000, 1)
    total = round(intent_ms + frame_ms, 1)
    return {
        "intent_ms": intent_ms,
        "frame_ms": frame_ms,
        "total_ms": total,
        "sla_ms": sla_ms,
        "sla_ok": total <= sla_ms,
    }


def deploy_readiness_snapshot() -> dict[str, Any]:
    summary = agents_status_summary()
    return {
        "agents_ready": summary.get("ready", 0),
        "agents_total": summary.get("total", 0),
        "all_ready": summary.get("all_ready", False),
        "redis": summary.get("redis", False),
        "livekit_configured": bool(
            os.getenv("LIVEKIT_URL") and os.getenv("LIVEKIT_API_KEY")
        ),
        "llm_configured": bool(os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")),
    }