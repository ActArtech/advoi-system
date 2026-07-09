"""Platform diagnostics — memory, OTel, squads, multi-agent readiness."""

from __future__ import annotations

import os
from typing import Any

from advoi.cache.agent_cache import agents_status_summary
from advoi.cache.redis_client import redis_available
from advoi.memory.operational_bridge import operational_diagnostics
from advoi.squads.registry import squads_summary


def otel_diagnostics() -> dict[str, Any]:
    enabled = os.getenv("OTEL_ENABLED", "false").lower() in {"1", "true", "yes"}
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://127.0.0.1:4317")
    packages_ok = False
    if enabled:
        try:
            import opentelemetry  # noqa: F401

            packages_ok = True
        except ImportError:
            packages_ok = False
    return {
        "enabled": enabled,
        "endpoint": endpoint,
        "packages_installed": packages_ok,
        "instrumented": enabled and packages_ok,
    }


async def platform_diagnostics() -> dict[str, Any]:
    agents = agents_status_summary()
    memory = await operational_diagnostics()
    squads = squads_summary()
    otel = otel_diagnostics()
    letta_on = memory.get("letta_enabled", False)
    return {
        "ok": True,
        "stage": "platform-m4",
        "agents": agents,
        "redis": redis_available(),
        "memory": memory,
        "letta_enabled": letta_on,
        "operational_bridge": "letta" if letta_on else "operational_store",
        "otel": otel,
        "squads": squads,
        "multi_agent": {
            "specialist_count": agents.get("total", 0),
            "ready": agents.get("ready", 0),
            "all_ready": agents.get("all_ready", False),
        },
    }