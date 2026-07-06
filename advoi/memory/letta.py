"""Letta integration — optional operational/identity memory (ADR-026 v0.2)."""

from __future__ import annotations

import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)


def _auth_headers() -> dict[str, str]:
    import os

    token = os.getenv("LETTA_API_KEY") or os.getenv("LETTA_SERVER_PASSWORD", "")
    return {"Authorization": f"Bearer {token}"} if token else {}


async def recall_operational(
    query: str,
    *,
    base_url: str,
    agent_id: str,
) -> list[dict[str, Any]]:
    """Search Letta archival memory (passages). Enable with LETTA_ENABLED=true."""
    if not base_url:
        return []
    try:
        import httpx

        headers = _auth_headers()
        async with httpx.AsyncClient(base_url=base_url, timeout=15.0, headers=headers) as client:
            resp = await client.get(
                f"/v1/agents/{agent_id}/archival-memory/search",
                params={"query": query, "top_k": 8},
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


async def retain_operational(
    event_type: str,
    payload: dict[str, Any],
    *,
    base_url: str,
    agent_id: str,
) -> bool:
    if not base_url:
        return False
    summary = payload.get("summary") or payload.get("text") or str(payload)[:2000]
    try:
        import httpx

        headers = _auth_headers()
        async with httpx.AsyncClient(base_url=base_url, timeout=15.0, headers=headers) as client:
            resp = await client.post(
                f"/v1/agents/{agent_id}/archival-memory",
                json={"text": f"[{event_type}] {summary}"},
            )
            return resp.status_code in (200, 201)
    except Exception as exc:
        _LOGGER.debug("letta retain unavailable: %s", exc)
        return False