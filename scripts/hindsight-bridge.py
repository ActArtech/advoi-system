#!/usr/bin/env python3
"""Run Hindsight recall/retain inside the Hermes container (local daemon on :9077)."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from typing import Any


def _results_from_recall_response(data: Any) -> list[dict[str, Any]]:
    if data is None:
        return []
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


async def _client():
    from hindsight_client import Hindsight

    base_url = os.getenv("HINDSIGHT_API_URL", "http://127.0.0.1:9077").rstrip("/")
    return Hindsight(
        base_url=base_url,
        api_key=os.getenv("HINDSIGHT_API_KEY") or None,
        timeout=30.0,
    )


async def recall(query: str, limit: int) -> dict[str, Any]:
    bank_id = os.getenv("HINDSIGHT_BANK_ID", "advoi-portfolio")
    client = await _client()
    try:
        response = await client.arecall(
            bank_id,
            query,
            max_tokens=min(limit * 512, 4096),
            budget=os.getenv("HINDSIGHT_RECALL_BUDGET", "mid"),
        )
        return {"ok": True, "results": _results_from_recall_response(response)}
    finally:
        await client.aclose()


async def retain(event_type: str, summary: str, payload: dict[str, Any]) -> dict[str, Any]:
    bank_id = os.getenv("HINDSIGHT_BANK_ID", "advoi-portfolio")
    metadata = {"event_type": event_type, "source": "advoi"}
    for key in ("project", "venture", "session_id"):
        if payload.get(key):
            metadata[key] = str(payload[key])
    client = await _client()
    try:
        await client.aretain(
            bank_id,
            summary,
            context=f"ADVoi {event_type}",
            metadata=metadata,
            tags=[event_type, "advoi"],
            retain_async=True,
        )
        return {"ok": True}
    finally:
        await client.aclose()


async def main_async(payload: dict[str, Any]) -> dict[str, Any]:
    action = payload.get("action")
    if action == "recall":
        return await recall(payload.get("query", ""), int(payload.get("limit", 8)))
    if action == "retain":
        return await retain(
            payload.get("event_type", "portfolio_fact"),
            payload.get("summary", ""),
            payload.get("payload", {}),
        )
    return {"ok": False, "error": f"unknown action: {action}"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", required=True, help="JSON payload")
    args = parser.parse_args()
    payload = json.loads(args.json)
    result = asyncio.run(main_async(payload))
    print(json.dumps(result))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())