"""Filesystem store for ingestion inbox + index."""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

from advoi.ingestion.models import IngestItem, IngestStatus

_INDEX_VERSION = 1


def ingestion_root() -> Path:
    return Path(os.getenv("ADVOI_INGESTION_PATH", "data/ingestion"))


def _index_path() -> Path:
    return ingestion_root() / "index.json"


def _ensure_dirs() -> None:
    root = ingestion_root()
    root.mkdir(parents=True, exist_ok=True)
    (root / "inbox").mkdir(parents=True, exist_ok=True)


def _load_index() -> dict[str, Any]:
    _ensure_dirs()
    path = _index_path()
    if not path.is_file():
        return {"version": _INDEX_VERSION, "items": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data.get("items"), list):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return {"version": _INDEX_VERSION, "items": []}


def _save_index(data: dict[str, Any]) -> None:
    _ensure_dirs()
    _index_path().write_text(json.dumps(data, indent=2), encoding="utf-8")


def _item_from_dict(raw: dict[str, Any]) -> IngestItem:
    return IngestItem(
        id=str(raw["id"]),
        filename=str(raw.get("filename", "unknown")),
        status=raw.get("status", "uploaded"),
        venture_id=raw.get("venture_id"),
        project_slug=raw.get("project_slug"),
        route_confidence=float(raw.get("route_confidence") or 0),
        priority=raw.get("priority", "medium"),
        priority_score=int(raw.get("priority_score") or 50),
        dev_recommended=bool(raw.get("dev_recommended")),
        summary=str(raw.get("summary") or ""),
        task_hint=str(raw.get("task_hint") or ""),
        content_preview=str(raw.get("content_preview") or ""),
        size_bytes=int(raw.get("size_bytes") or 0),
        mime_type=raw.get("mime_type"),
        error=raw.get("error"),
        dispatch_result=raw.get("dispatch_result"),
        created_at=float(raw.get("created_at") or 0),
        updated_at=float(raw.get("updated_at") or 0),
        extra=dict(raw.get("extra") or {}),
    )


def list_items(*, status: IngestStatus | None = None) -> list[IngestItem]:
    items = [_item_from_dict(row) for row in _load_index().get("items", [])]
    if status:
        items = [i for i in items if i.status == status]
    return sorted(items, key=lambda i: i.created_at, reverse=True)


def get_item(item_id: str) -> IngestItem | None:
    for row in _load_index().get("items", []):
        if row.get("id") == item_id:
            return _item_from_dict(row)
    return None


def save_item(item: IngestItem) -> IngestItem:
    data = _load_index()
    rows = data.setdefault("items", [])
    payload = item.to_dict()
    for idx, row in enumerate(rows):
        if row.get("id") == item.id:
            rows[idx] = payload
            _save_index(data)
            return item
    rows.append(payload)
    _save_index(data)
    return item


def create_upload(
    filename: str,
    data: bytes,
    *,
    mime_type: str | None = None,
) -> IngestItem:
    _ensure_dirs()
    item_id = uuid.uuid4().hex[:12]
    blob_dir = ingestion_root() / "inbox" / item_id
    blob_dir.mkdir(parents=True, exist_ok=True)
    (blob_dir / "original").write_bytes(data)
    now = time.time()
    item = IngestItem(
        id=item_id,
        filename=filename,
        size_bytes=len(data),
        mime_type=mime_type,
        created_at=now,
        updated_at=now,
    )
    return save_item(item)


def read_original(item_id: str) -> bytes | None:
    path = ingestion_root() / "inbox" / item_id / "original"
    if not path.is_file():
        return None
    return path.read_bytes()