"""Operational memory bridge — Letta when enabled, JSONL store otherwise."""

from __future__ import annotations

from typing import Any

from advoi.memory.letta_client import load_letta_config, probe_health, recall_passages, retain_passage
from advoi.memory.operational_store import append_operational, recall_operational_local


async def recall_operational_unified(query: str, *, limit: int = 8) -> tuple[list[dict[str, Any]], str]:
    """Returns (rows, source_label)."""
    cfg = load_letta_config()
    if cfg.enabled:
        rows = await recall_passages(query, cfg=cfg, top_k=limit)
        if rows:
            return rows, "letta"
    local = await recall_operational_local(query, limit=limit)
    return local, "operational_store" if local else "none"


async def retain_operational_unified(
    event_type: str,
    payload: dict[str, Any],
) -> dict[str, bool]:
    """Write to Letta and/or local store per ADR-026."""
    cfg = load_letta_config()
    results: dict[str, bool] = {}
    if cfg.enabled:
        results["letta"] = await retain_passage(event_type, payload, cfg=cfg)
    results["operational_store"] = await append_operational(event_type, payload)
    return results


async def operational_diagnostics() -> dict[str, Any]:
    cfg = load_letta_config()
    health = await probe_health(cfg) if cfg.enabled else {"ok": False, "reason": "disabled"}
    return {
        "letta_enabled": cfg.enabled,
        "letta_base_url": bool(cfg.base_url),
        "letta_health": health,
    }