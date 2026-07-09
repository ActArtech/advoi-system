"""Diagnostic decision frames — memory, latency, guardian, deploy readiness."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from advoi.copy_style import plain_copy
from advoi.diagnostics.probes import (
    deploy_readiness_snapshot,
    memory_health_snapshot,
    quick_latency_ms,
)
from advoi.guardian.confirmation import (
    frame_needs_confirmation,
    global_confirmation_enabled,
    high_risk_fleet_actions,
)


def _guardian_log_tail(limit: int = 5) -> list[dict[str, Any]]:
    path = Path(os.getenv("GUARDIAN_LOG_PATH", "docs/error-log/guardian-events.jsonl"))
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    try:
        for line in reversed(path.read_text(encoding="utf-8").splitlines()):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
            if len(rows) >= limit:
                break
    except OSError:
        return []
    return rows


async def run_memory_health() -> tuple[str, dict[str, Any], str]:
    snap = await memory_health_snapshot()
    mode = snap.get("memory_bridge_mode", "unknown")
    bridge_ok = snap.get("memory_bridge_ok", False)
    parts = [
        f"Memory provider is {snap.get('provider', 'unknown')}.",
        f"Bridge mode {mode}" + (" and healthy." if bridge_ok else "."),
    ]
    if snap.get("redis_configured"):
        parts.append("Redis is configured.")
    if snap.get("postgres_configured"):
        parts.append("Postgres is configured.")
    if snap.get("operational_store_exists"):
        parts.append("Operational store has entries.")
    spoken = plain_copy(" ".join(parts))
    return spoken, {"snapshot": snap}, "ok"


async def run_latency_check() -> tuple[str, dict[str, Any], str]:
    timing = await quick_latency_ms()
    sla_ok = timing.get("sla_ok", False)
    spoken = plain_copy(
        f"Latency probe: intent {timing['intent_ms']}ms, frame {timing['frame_ms']}ms, "
        f"total {timing['total_ms']}ms. SLA target {timing['sla_ms']}ms. "
        f"{'Within SLA.' if sla_ok else 'Over SLA.'}"
    )
    status = "ok" if sla_ok else "degraded"
    return spoken, {"timing": timing}, status


async def run_guardian_status() -> tuple[str, dict[str, Any], str]:
    high_risk_frames = [
        fid for fid in ("queue_deep_review",) if frame_needs_confirmation(fid)
    ]
    high_risk_ops = high_risk_fleet_actions()
    events = _guardian_log_tail()
    recent_failures = sum(
        1 for e in events if e.get("event_type") == "agent_tick_failed"
    )
    spoken = plain_copy(
        f"Guardian: confirmation {'on' if global_confirmation_enabled() else 'off'}. "
        f"{len(high_risk_frames)} high-risk frame(s). "
        f"{len(high_risk_ops)} high-risk fleet action(s) including start development. "
        f"{recent_failures} recent agent failure event(s) in log."
    )
    return spoken, {
        "confirmation_enabled": global_confirmation_enabled(),
        "high_risk_frames": high_risk_frames,
        "high_risk_fleet_actions": high_risk_ops,
        "recent_events": len(events),
        "recent_failures": recent_failures,
    }, "ok"


async def run_deploy_readiness() -> tuple[str, dict[str, Any], str]:
    snap = deploy_readiness_snapshot()
    ready = int(snap.get("agents_ready") or 0)
    total = int(snap.get("agents_total") or 0)
    checks = [
        snap.get("redis"),
        snap.get("livekit_configured"),
        snap.get("llm_configured"),
    ]
    ok_count = sum(1 for c in checks if c)
    spoken = plain_copy(
        f"Deploy readiness: {ready} of {total} agents cached. "
        f"{ok_count} of 3 infra checks passed "
        f"(redis, livekit, llm)."
    )
    status = "ok" if snap.get("all_ready") and ok_count >= 2 else "degraded"
    return spoken, {"snapshot": snap}, status