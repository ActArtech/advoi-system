"""Hindsight integration — strategic memory via hindsight-client (ADR-026)."""

from __future__ import annotations

import json
import logging
import os
import subprocess
from functools import lru_cache
from typing import Any

_LOGGER = logging.getLogger(__name__)

DEFAULT_CLOUD_URL = "https://api.hindsight.vectorize.io"
DEFAULT_LOCAL_URL = "http://127.0.0.1:9077"
DEFAULT_BANK_ID = "advoi-portfolio"


@lru_cache(maxsize=1)
def _hindsight_settings() -> dict[str, str]:
    mode = os.getenv("HINDSIGHT_MODE", "local").lower()
    bridge = os.getenv("HINDSIGHT_BRIDGE", "").lower()
    api_url = os.getenv("HINDSIGHT_API_URL", "")
    if not api_url:
        api_url = DEFAULT_CLOUD_URL if mode == "cloud" else DEFAULT_LOCAL_URL
    return {
        "mode": mode,
        "bridge": bridge,
        "api_url": api_url.rstrip("/"),
        "api_key": os.getenv("HINDSIGHT_API_KEY", ""),
        "bank_id": os.getenv("HINDSIGHT_BANK_ID", DEFAULT_BANK_ID),
        "hermes_container": os.getenv("HERMES_CONTAINER", "hermes"),
    }


def _results_from_recall_response(data: Any) -> list[dict[str, Any]]:
    if data is None:
        return []
    if isinstance(data, list):
        return [item if isinstance(item, dict) else {"text": str(item)} for item in data]
    if isinstance(data, dict):
        for key in ("results", "memories", "facts", "observations"):
            items = data.get(key)
            if isinstance(items, list):
                return [item if isinstance(item, dict) else {"text": str(item)} for item in items]
        text = data.get("text") or data.get("content") or data.get("summary")
        if text:
            return [{"source": "hindsight", "text": str(text)}]
    text_attr = getattr(data, "to_prompt_string", None)
    if callable(text_attr):
        text = text_attr()
        if text:
            return [{"source": "hindsight", "text": text}]
    for attr in ("results", "memories", "facts"):
        items = getattr(data, attr, None)
        if isinstance(items, list):
            return [item if isinstance(item, dict) else {"text": str(item)} for item in items]
    return []


async def _recall_direct(query: str, *, limit: int) -> list[dict[str, Any]]:
    from hindsight_client import Hindsight

    cfg = _hindsight_settings()
    client = Hindsight(
        base_url=cfg["api_url"],
        api_key=cfg["api_key"] or None,
        timeout=30.0,
    )
    try:
        response = await client.arecall(
            cfg["bank_id"],
            query,
            max_tokens=min(limit * 512, 4096),
            budget=os.getenv("HINDSIGHT_RECALL_BUDGET", "mid"),
        )
        return _results_from_recall_response(response)
    finally:
        await client.aclose()


async def _retain_direct(
    event_type: str,
    summary: str,
    payload: dict[str, Any],
) -> bool:
    from hindsight_client import Hindsight

    cfg = _hindsight_settings()
    metadata = {
        "event_type": event_type,
        "source": "advoi",
    }
    for key in ("project", "venture", "session_id"):
        if payload.get(key):
            metadata[key] = str(payload[key])

    client = Hindsight(
        base_url=cfg["api_url"],
        api_key=cfg["api_key"] or None,
        timeout=30.0,
    )
    try:
        await client.aretain(
            cfg["bank_id"],
            summary,
            context=f"ADVoi {event_type}",
            metadata=metadata,
            tags=[event_type, "advoi"],
            retain_async=True,
        )
        return True
    finally:
        await client.aclose()


def _bridge_payload(action: str, **kwargs: Any) -> str:
    return json.dumps({"action": action, **kwargs})


def _docker_exec_available() -> bool:
    import shutil

    return shutil.which("docker") is not None


async def _http_bridge_call(action: str, **kwargs: Any) -> Any:
    url = os.getenv("HINDSIGHT_BRIDGE_URL", "").rstrip("/")
    if not url:
        return None
    import httpx

    path = "/recall" if action == "recall" else "/retain"
    if action == "recall":
        body = {"query": kwargs.get("query", ""), "limit": int(kwargs.get("limit", 8))}
    else:
        body = {
            "event_type": kwargs.get("event_type", "portfolio_fact"),
            "summary": kwargs.get("summary", ""),
            "payload": kwargs.get("payload", {}),
        }
    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(f"{url}{path}", json=body)
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:
        _LOGGER.debug("hindsight http bridge failed: %s", exc)
        return None


async def _bridge_call(action: str, **kwargs: Any) -> Any:
    http_result = await _http_bridge_call(action, **kwargs)
    if isinstance(http_result, dict) and http_result.get("ok") is not None:
        return http_result

    cfg = _hindsight_settings()
    if not _docker_exec_available():
        _LOGGER.debug("hindsight bridge skip: no HTTP bridge and docker CLI unavailable")
        return None
    script = os.getenv(
        "HINDSIGHT_BRIDGE_SCRIPT",
        "/vps-projects/advoi/scripts/hindsight-bridge.py",
    )
    payload = _bridge_payload(action, **kwargs)
    proc = subprocess.run(
        [
            "docker",
            "exec",
            cfg["hermes_container"],
            "python",
            script,
            "--json",
            payload,
        ],
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )
    if proc.returncode != 0:
        _LOGGER.debug("hindsight bridge failed: %s", proc.stderr.strip() or proc.stdout.strip())
        return None
    try:
        return json.loads(proc.stdout.strip() or "{}")
    except json.JSONDecodeError:
        _LOGGER.debug("hindsight bridge invalid json: %s", proc.stdout[:200])
        return None


async def recall_strategic(
    query: str,
    *,
    hermes_container: str = "hermes",  # noqa: ARG001 — kept for router API compat
    limit: int = 8,
) -> list[dict[str, Any]]:
    """Recall portfolio/governance context from Hindsight."""
    cfg = _hindsight_settings()
    try:
        use_bridge = (
            os.getenv("HINDSIGHT_BRIDGE_URL")
            or cfg["bridge"] == "hermes"
            or (cfg["mode"] == "local" and cfg["api_url"].startswith("http://127.0.0.1"))
        )
        if use_bridge:
            data = await _bridge_call("recall", query=query, limit=limit)
            if isinstance(data, dict) and data.get("ok"):
                return data.get("results", [])
            if os.getenv("HINDSIGHT_BRIDGE_URL"):
                return []

        return await _recall_direct(query, limit=limit)
    except Exception as exc:
        _LOGGER.debug("hindsight recall unavailable: %s", exc)
        return []


async def retain_strategic(
    event_type: str,
    payload: dict[str, Any],
    *,
    hermes_container: str = "hermes",  # noqa: ARG001 — kept for router API compat
) -> bool:
    """Retain strategic fact in Hindsight."""
    summary = payload.get("summary") or payload.get("text") or str(payload)[:2000]
    cfg = _hindsight_settings()
    try:
        use_bridge = (
            os.getenv("HINDSIGHT_BRIDGE_URL")
            or cfg["bridge"] == "hermes"
            or (cfg["mode"] == "local" and cfg["api_url"].startswith("http://127.0.0.1"))
        )
        if use_bridge:
            data = await _bridge_call(
                "retain",
                event_type=event_type,
                summary=summary,
                payload=payload,
            )
            return bool(isinstance(data, dict) and data.get("ok"))

        return await _retain_direct(event_type, summary, payload)
    except Exception as exc:
        _LOGGER.debug("hindsight retain unavailable: %s", exc)
        return False