"""Local operational memory — JSONL fallback when Letta is off (Phase 4.1 dev path)."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_LOGGER = logging.getLogger(__name__)

def _store_path() -> Path:
    return Path(os.getenv("ADVOI_OPERATIONAL_STORE", "data/operational-memory.jsonl"))


def _store_enabled() -> bool:
    return os.getenv("ADVOI_OPERATIONAL_STORE_ENABLED", "true").lower() in {
        "1",
        "true",
        "yes",
    }


async def append_operational(event_type: str, payload: dict[str, Any]) -> bool:
    if not _store_enabled():
        return False
    try:
        path = _store_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "summary": payload.get("summary") or payload.get("spoken_summary") or "",
            "agent_id": payload.get("agent_id"),
            "frame_id": payload.get("frame_id"),
            "status": payload.get("status"),
            "payload": payload,
        }
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
        return True
    except Exception as exc:
        _LOGGER.debug("operational store append failed: %s", exc)
        return False


async def recall_operational_local(query: str, *, limit: int = 8) -> list[dict[str, Any]]:
    path = _store_path()
    if not _store_enabled() or not path.exists():
        return []
    needle = (query or "").strip().lower()
    rows: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        for line in reversed(lines):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            text = str(row.get("summary") or "")
            haystack = " ".join(
                [
                    text,
                    str(row.get("frame_id", "")),
                    str(row.get("event_type", "")),
                    json.dumps(row.get("payload") or {}, default=str),
                ]
            ).lower()
            if not needle or needle in haystack or needle in str(row.get("agent_id", "")).lower():
                rows.append({"source": "operational_store", "text": text, "meta": row})
            if len(rows) >= limit:
                break
    except Exception as exc:
        _LOGGER.debug("operational store recall failed: %s", exc)
    return rows