"""Ingestion pipeline: upload → parse → route → optional FirstMate dev dispatch."""

from __future__ import annotations

import logging
import time
from typing import Any

from advoi.fleet.trigger import fleet_trigger_from_voice, invoke_fleet_trigger
from advoi.ingestion.parse import extract_text
from advoi.ingestion.route import apply_route, route_document
from advoi.ingestion.store import create_upload, get_item, list_items, read_original, save_item
from advoi.ingestion.models import IngestItem

_LOGGER = logging.getLogger(__name__)


async def ingest_upload(
    filename: str,
    data: bytes,
    *,
    mime_type: str | None = None,
    project_hint: str | None = None,
    venture_hint: str | None = None,
) -> IngestItem:
    item = create_upload(filename, data, mime_type=mime_type)
    try:
        text = extract_text(filename, data)
        route = route_document(
            text,
            filename,
            project_hint=project_hint,
            venture_hint=venture_hint,
        )
        item = apply_route(item, route, text=text)
        item.updated_at = time.time()
        return save_item(item)
    except Exception as exc:
        _LOGGER.warning("ingestion failed for %s: %s", filename, exc)
        item.status = "failed"
        item.error = str(exc)
        item.updated_at = time.time()
        return save_item(item)


async def reroute_item(item_id: str, *, project_hint: str | None = None) -> IngestItem:
    item = get_item(item_id)
    if not item:
        raise ValueError(f"Unknown ingestion item: {item_id}")
    raw = read_original(item_id)
    if raw is None:
        raise ValueError(f"Missing file blob for {item_id}")
    text = extract_text(item.filename, raw)
    route = route_document(text, item.filename, project_hint=project_hint)
    item = apply_route(item, route, text=text)
    item.updated_at = time.time()
    return save_item(item)


async def dispatch_item_dev(
    item_id: str,
    *,
    confirmed: bool = False,
    mode: str = "work",
) -> dict[str, Any]:
    item = get_item(item_id)
    if not item:
        return {"ok": False, "status": "not_found", "item_id": item_id}

    if item.status == "failed":
        return {"ok": False, "status": "failed", "error": item.error, "item_id": item_id}

    from advoi.guardian.confirmation import evaluate_fleet_confirmation

    guardian_action = "start_development" if mode == "start_development" else "run_next_backlog"
    gate = evaluate_fleet_confirmation(guardian_action, confirmed=confirmed)
    if not gate["proceed"]:
        return {
            "ok": False,
            "status": "confirmation_required",
            "item_id": item_id,
            "project_slug": item.project_slug,
            "task_hint": item.task_hint,
            "guardian": True,
            "spoken": str(
                gate.get(
                    "prompt",
                    "Confirm yes to dispatch this ingestion item to FirstMate development.",
                )
            ),
        }

    project = item.project_slug or "clapart"
    task = item.task_hint or item.summary or f"Process ingested file {item.filename}"

    if mode == "start_development":
        transcript = f"start development on {project} confirm"
        result = await fleet_trigger_from_voice(
            "start_development",
            transcript=transcript,
            confirmed=True,
        )
    else:
        arm = await invoke_fleet_trigger("arm", project=project)
        work = await invoke_fleet_trigger(f"work {task}", project=project)
        result = {
            "ok": arm.get("ok") and work.get("ok"),
            "status": "dispatched" if arm.get("ok") and work.get("ok") else "failed",
            "arm": arm,
            "work": work,
            "project": project,
            "task": task,
        }
        if result["ok"]:
            result["spoken"] = (
                f"Dispatched ingestion item to FirstMate on {project}. "
                f"Task: {task[:120]}"
            )

    if result.get("ok"):
        item.status = "dispatched"
        item.dispatch_result = {k: v for k, v in result.items() if k != "spoken"}
        item.updated_at = time.time()
        save_item(item)

    return {**result, "item_id": item_id, "item": item.to_dict()}


def ingestion_summary() -> dict[str, Any]:
    items = list_items()
    by_status: dict[str, int] = {}
    for item in items:
        by_status[item.status] = by_status.get(item.status, 0) + 1
    return {
        "total": len(items),
        "by_status": by_status,
        "pending_dev": sum(
            1 for i in items if i.status == "routed" and i.dev_recommended
        ),
    }