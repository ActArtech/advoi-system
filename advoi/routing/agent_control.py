"""Agent daemon control — pause ticks, clear cache, optional Docker restart."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import Any

from advoi.cache.agent_cache import agents_status_summary, cache_key
from advoi.cache.redis_client import get_redis, redis_available
from advoi.routing.agent_bootstrap import prewarm_all_agents
from advoi.routing.agent_config import AGENT_FRAMES
from advoi.routing.agents import AGENTS

_LOGGER = logging.getLogger(__name__)

PAUSE_KEY = "advoi:agents:paused"
CONTROL_META_KEY = "advoi:agents:control_meta"

DOCKER_AGENT_SERVICES: dict[str, str] = {
    "fleet-scout": "advoi-agent-fleet",
    "brief-curator": "advoi-agent-briefs",
    "review-queue": "advoi-agent-review",
    "systems-pulse": "advoi-agent-systems",
    "memory-scout": "advoi-agent-memory",
    "guardian-sentinel": "advoi-agent-guardian",
}

ALL_DOCKER_SERVICES = tuple(DOCKER_AGENT_SERVICES.values())

# Fallback when Redis is down (local dev, tests).
_local_paused = False


def _docker_control_enabled() -> bool:
    return os.getenv("ADVOI_DAEMON_DOCKER_CONTROL", "false").lower() in {
        "1",
        "true",
        "yes",
    }


def agents_paused() -> bool:
    global _local_paused
    client = get_redis()
    if not client:
        return _local_paused
    try:
        return client.get(PAUSE_KEY) == "1"
    except Exception:
        return _local_paused


def _write_control_meta(action: str, *, detail: dict[str, Any] | None = None) -> None:
    client = get_redis()
    if not client:
        return
    payload = {
        "action": action,
        "ts": time.time(),
        "paused": agents_paused(),
        "detail": detail or {},
    }
    try:
        client.setex(CONTROL_META_KEY, 86400, json.dumps(payload))
    except Exception as exc:
        _LOGGER.debug("control meta write skip: %s", exc)


def set_agents_paused(paused: bool) -> bool:
    global _local_paused
    _local_paused = paused
    client = get_redis()
    if not client:
        return True
    try:
        if paused:
            client.set(PAUSE_KEY, "1")
        else:
            client.delete(PAUSE_KEY)
        return True
    except Exception as exc:
        _LOGGER.warning("set_agents_paused failed: %s", exc)
        return True


def clear_all_agent_caches() -> int:
    client = get_redis()
    if not client:
        return 0
    keys = [cache_key(aid) for aid in AGENT_FRAMES]
    try:
        deleted = client.delete(*keys) if keys else 0
        return int(deleted or 0)
    except Exception as exc:
        _LOGGER.warning("clear agent caches failed: %s", exc)
        return 0


async def _docker_compose(action: str, services: tuple[str, ...]) -> dict[str, Any]:
    """Run docker compose stop|restart for agent daemon services."""
    if not services:
        return {"ok": False, "reason": "no_services"}
    from pathlib import Path

    compose_file = os.getenv("ADVOI_COMPOSE_FILE", "docker-compose.yml")
    env_file = os.getenv("ADVOI_ENV_FILE", "deploy/.env")
    staging = os.getenv("ADVOI_COMPOSE_STAGING", "deploy/docker-compose.staging.yml")
    root = Path(os.getenv("ADVOI_PROJECT_ROOT", "."))
    cmd = ["docker", "compose", "--env-file", str(root / env_file), "-f", str(root / compose_file)]
    staging_path = root / staging
    if staging_path.is_file():
        cmd.extend(["-f", str(staging_path)])
    cmd.extend([action, *services])
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(root),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120.0)
        ok = proc.returncode == 0
        return {
            "ok": ok,
            "action": action,
            "services": list(services),
            "exit_code": proc.returncode,
            "stdout": (stdout or b"").decode("utf-8", errors="replace")[-500:],
            "stderr": (stderr or b"").decode("utf-8", errors="replace")[-500:],
        }
    except Exception as exc:
        return {"ok": False, "action": action, "error": str(exc)}


def daemon_control_status() -> dict[str, Any]:
    summary = agents_status_summary()
    client = get_redis()
    meta: dict[str, Any] | None = None
    if client:
        try:
            raw = client.get(CONTROL_META_KEY)
            if raw:
                meta = json.loads(raw)
        except Exception:
            meta = None
    return {
        "paused": agents_paused(),
        "redis": redis_available(),
        "docker_control": _docker_control_enabled(),
        "agents_ready": summary.get("ready", 0),
        "agents_total": summary.get("total", 0),
        "last_control": meta,
    }


async def stop_agent_daemons(
    *,
    docker: bool | None = None,
    clear_cache: bool = True,
) -> dict[str, Any]:
    """Pause background ticks and optionally stop Docker agent containers."""
    use_docker = _docker_control_enabled() if docker is None else docker
    set_agents_paused(True)
    cleared = clear_all_agent_caches() if clear_cache else 0
    docker_result: dict[str, Any] | None = None
    if use_docker:
        docker_result = await _docker_compose("stop", ALL_DOCKER_SERVICES)
    result = {
        "ok": True,
        "action": "stop",
        "paused": True,
        "caches_cleared": cleared,
        "docker": docker_result,
    }
    _write_control_meta("stop", detail=result)
    return result


async def restart_agent_daemons(
    *,
    docker: bool | None = None,
    prewarm: bool = True,
) -> dict[str, Any]:
    """Resume ticks, optionally restart Docker containers, and prewarm cache."""
    use_docker = _docker_control_enabled() if docker is None else docker
    set_agents_paused(False)
    docker_result: dict[str, Any] | None = None
    if use_docker:
        docker_result = await _docker_compose("restart", ALL_DOCKER_SERVICES)
    prewarmed = 0
    summary: dict[str, Any] = {}
    if prewarm:
        rows = await prewarm_all_agents()
        prewarmed = len(rows)
        summary = agents_status_summary()
    result = {
        "ok": True,
        "action": "restart",
        "paused": False,
        "prewarmed": prewarmed,
        "agents_ready": summary.get("ready", 0),
        "agents_total": summary.get("total", len(AGENTS)),
        "docker": docker_result,
    }
    _write_control_meta("restart", detail=result)
    return result


def spoken_stop_agents(result: dict[str, Any]) -> str:
    cleared = result.get("caches_cleared", 0)
    parts = [
        "Background agent daemons are paused.",
        f"Cleared {cleared} warm cache entries.",
        "Ticks will idle until you say restart agents.",
    ]
    docker = result.get("docker")
    if docker and docker.get("ok"):
        parts.append("Docker agent containers stopped.")
    elif docker and not docker.get("ok"):
        parts.append("Docker stop was skipped or failed; Redis pause is still active.")
    return " ".join(parts)


def spoken_restart_agents(result: dict[str, Any]) -> str:
    ready = result.get("agents_ready", 0)
    total = result.get("agents_total", len(AGENTS))
    parts = [
        "Agent daemons restarted.",
        f"Prewarmed {ready} of {total} specialists.",
        "Say systems pulse for a full portfolio read.",
    ]
    docker = result.get("docker")
    if docker and docker.get("ok"):
        parts.append("Docker agent containers are back up.")
    return " ".join(parts)