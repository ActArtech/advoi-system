"""Platform diagnostics — memory, OTel, squads, multi-agent readiness."""

from __future__ import annotations

import os
from typing import Any

from advoi.cache.agent_cache import agents_status_summary
from advoi.cache.redis_client import redis_available
from advoi.memory.operational_bridge import operational_diagnostics
from advoi.observability.otel_setup import otel_enabled, probe_collector_reachable
from advoi.squads.registry import squads_summary


def otel_diagnostics() -> dict[str, Any]:
    """OTel readiness for T2 `/api/diagnostics/platform` (moat R6).

    ``otel_ready`` is true only when enabled, SDK packages are installed, and the
    OTLP collector endpoint accepts a TCP connection.
    """
    enabled = otel_enabled()
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://127.0.0.1:4317")
    packages_ok = False
    if enabled:
        try:
            import opentelemetry  # noqa: F401

            packages_ok = True
        except ImportError:
            packages_ok = False
    collector_reachable = False
    if enabled:
        collector_reachable = probe_collector_reachable(endpoint)
    instrumented = enabled and packages_ok
    otel_ready = instrumented and collector_reachable
    return {
        "enabled": enabled,
        "endpoint": endpoint,
        "packages_installed": packages_ok,
        "instrumented": instrumented,
        "collector_reachable": collector_reachable,
        "otel_ready": otel_ready,
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
        "otel_ready": otel.get("otel_ready", False),
        "squads": squads,
        "multi_agent": {
            "specialist_count": agents.get("total", 0),
            "ready": agents.get("ready", 0),
            "all_ready": agents.get("all_ready", False),
        },
    }
