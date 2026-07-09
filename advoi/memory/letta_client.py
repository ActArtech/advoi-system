"""Letta HTTP client — health, recall, retain (ADR-026 v0.2)."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

_LOGGER = logging.getLogger(__name__)


@dataclass
class LettaConfig:
    enabled: bool
    base_url: str
    agent_id: str
    api_key: str


def load_letta_config() -> LettaConfig:
    return LettaConfig(
        enabled=os.getenv("LETTA_ENABLED", "false").lower() == "true",
        base_url=os.getenv("LETTA_BASE_URL", "http://letta:8283").rstrip("/"),
        agent_id=os.getenv("LETTA_AGENT_ID", "advoi-executive"),
        api_key=os.getenv("LETTA_API_KEY") or os.getenv("LETTA_SERVER_PASSWORD", ""),
    )


def _headers(cfg: LettaConfig) -> dict[str, str]:
    return {"Authorization": f"Bearer {cfg.api_key}"} if cfg.api_key else {}


async def probe_health(cfg: LettaConfig | None = None) -> dict[str, Any]:
    """Check Letta reachability without failing the caller."""
    c = cfg or load_letta_config()
    if not c.enabled or not c.base_url:
        return {"ok": False, "reason": "disabled"}
    try:
        import httpx

        async with httpx.AsyncClient(
            base_url=c.base_url, timeout=8.0, headers=_headers(c)
        ) as client:
            resp = await client.get(f"/v1/agents/{c.agent_id}")
            if resp.status_code == 200:
                return {"ok": True, "agent_id": c.agent_id, "base_url": c.base_url}
            return {
                "ok": False,
                "status_code": resp.status_code,
                "preview": resp.text[:200],
            }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


async def recall_passages(
    query: str,
    *,
    cfg: LettaConfig | None = None,
    top_k: int = 8,
) -> list[dict[str, Any]]:
    c = cfg or load_letta_config()
    if not c.enabled or not c.base_url:
        return []
    try:
        import httpx

        async with httpx.AsyncClient(
            base_url=c.base_url, timeout=15.0, headers=_headers(c)
        ) as client:
            resp = await client.get(
                f"/v1/agents/{c.agent_id}/archival-memory/search",
                params={"query": query, "top_k": top_k},
            )
            if resp.status_code != 200:
                _LOGGER.debug("letta recall %s: %s", resp.status_code, resp.text[:200])
                return []
            data = resp.json()
            passages = data.get("results", []) if isinstance(data, dict) else data
            return [
                {"source": "letta", "text": p.get("content") or p.get("text") or str(p)}
                for p in passages
                if isinstance(p, dict)
            ]
    except Exception as exc:
        _LOGGER.debug("letta recall unavailable: %s", exc)
        return []


async def retain_passage(
    event_type: str,
    payload: dict[str, Any],
    *,
    cfg: LettaConfig | None = None,
) -> bool:
    c = cfg or load_letta_config()
    if not c.enabled or not c.base_url:
        return False
    summary = payload.get("summary") or payload.get("text") or str(payload)[:2000]
    try:
        import httpx

        async with httpx.AsyncClient(
            base_url=c.base_url, timeout=15.0, headers=_headers(c)
        ) as client:
            resp = await client.post(
                f"/v1/agents/{c.agent_id}/archival-memory",
                json={"text": f"[{event_type}] {summary}"},
            )
            return resp.status_code in (200, 201)
    except Exception as exc:
        _LOGGER.debug("letta retain unavailable: %s", exc)
        return False