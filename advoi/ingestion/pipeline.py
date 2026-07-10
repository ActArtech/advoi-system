"""Ingestion pipeline: upload → triage → needs_review → approve → dispatch.

Upload creates an ``uploaded`` item only (no auto-dispatch). Lifecycle
transitions are explicit; dispatch requires ``approved`` (moat R4 / M7).

Optional ``auto_triage`` on upload (default off) runs the M7.2 keyword
classifier and may advance to ``triaged`` or ``needs_review``.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from advoi.fleet.trigger import fleet_trigger_from_voice, invoke_fleet_trigger
from advoi.ingestion.lifecycle import (
    InvalidTransitionError,
    can_dispatch,
    transition,
)
from advoi.ingestion.models import IngestItem, IngestStatus
from advoi.ingestion.parse import extract_text
from advoi.ingestion.route import apply_route, route_document
from advoi.ingestion.store import create_upload, get_item, list_items, read_original, save_item
from advoi.ingestion.triage import apply_triage_result, classify_item
from advoi.ontology import OntologyValidationError

_LOGGER = logging.getLogger(__name__)


def _touch(item: IngestItem) -> IngestItem:
    item.updated_at = time.time()
    return item


def _apply_status(item: IngestItem, to_status: IngestStatus) -> IngestItem:
    item.status = transition(item.status, to_status, item_id=item.id)
    return _touch(item)


async def ingest_upload(
    filename: str,
    data: bytes,
    *,
    mime_type: str | None = None,
    project_hint: str | None = None,
    venture_hint: str | None = None,
    paperclip_ticket_id: str | None = None,
    auto_triage: bool = False,
) -> IngestItem:
    """Create an inbox item and attach route metadata; leave status ``uploaded``.

    Does not auto-dispatch. Call :func:`triage_item` / :func:`approve_item` /
    :func:`dispatch_item_dev` for later lifecycle steps.

    When ``auto_triage`` is True, run the keyword classifier after upload and
    advance toward ``triaged`` or ``needs_review`` (still never to approved/
    dispatched). Default is False so upload remains a pure intake step.
    """
    item = create_upload(
        filename,
        data,
        mime_type=mime_type,
        paperclip_ticket_id=paperclip_ticket_id,
    )
    try:
        text = extract_text(filename, data)
        route = route_document(
            text,
            filename,
            project_hint=project_hint,
            venture_hint=venture_hint,
        )
        # Metadata only — status stays uploaded (no routed / no dispatch).
        item = apply_route(item, route, text=text, set_routed=False)
        item.status = "uploaded"
        item = save_item(_touch(item))
    except OntologyValidationError as exc:
        # Persist failed item (recoverable via re-route) then re-raise for API 422.
        _LOGGER.warning("ingestion route rejected for %s: %s", filename, exc.detail)
        item.status = "failed"
        item.error = exc.detail
        save_item(_touch(item))
        raise
    except Exception as exc:
        _LOGGER.warning("ingestion failed for %s: %s", filename, exc)
        item.status = "failed"
        item.error = str(exc)
        return save_item(_touch(item))

    if auto_triage and item.status == "uploaded":
        return await triage_item(item.id, project_hint=project_hint)
    return item


async def triage_item(
    item_id: str,
    *,
    project_hint: str | None = None,
    apply_classifier: bool = True,
) -> IngestItem:
    """Transition ``uploaded`` → ``triaged``, optionally auto-advance further.

    Re-routes when the original blob is present, then runs the M7.2 keyword
    classifier (:mod:`advoi.ingestion.triage`). Classifier output is stored on
    ``item.extra['triage']``.

    When ``apply_classifier`` is True (default) and the classifier target is
    ``needs_review``, the item advances ``uploaded → triaged → needs_review``
    in one call. Clear routes stop at ``triaged``.
    """
    item = get_item(item_id)
    if not item:
        raise ValueError(f"Unknown ingestion item: {item_id}")

    text: str | None = None
    raw = read_original(item_id)
    if raw is not None:
        text = extract_text(item.filename, raw)
        route = route_document(text, item.filename, project_hint=project_hint)
        item = apply_route(item, route, text=text, set_routed=False)

    if apply_classifier:
        result = classify_item(item, text=text)
        item = apply_triage_result(item, result)
        target = result.target_status
    else:
        target = "triaged"

    # Always step through triaged first (state machine forbids uploaded→needs_review).
    if item.status == "uploaded":
        item = _apply_status(item, "triaged")

    if apply_classifier and target == "needs_review" and item.status == "triaged":
        item = _apply_status(item, "needs_review")

    return save_item(item)


async def mark_needs_review(item_id: str) -> IngestItem:
    """Transition ``triaged`` (or legacy ``routed``) → ``needs_review``."""
    item = get_item(item_id)
    if not item:
        raise ValueError(f"Unknown ingestion item: {item_id}")
    item = _apply_status(item, "needs_review")
    return save_item(item)


async def approve_item(item_id: str) -> IngestItem:
    """Transition ``needs_review`` (or legacy ``routed``) → ``approved``."""
    item = get_item(item_id)
    if not item:
        raise ValueError(f"Unknown ingestion item: {item_id}")
    item = _apply_status(item, "approved")
    return save_item(item)


async def reroute_item(item_id: str, *, project_hint: str | None = None) -> IngestItem:
    """Re-run routing metadata. Does not auto-advance lifecycle or dispatch."""
    item = get_item(item_id)
    if not item:
        raise ValueError(f"Unknown ingestion item: {item_id}")
    raw = read_original(item_id)
    if raw is None:
        raise ValueError(f"Missing file blob for {item_id}")
    text = extract_text(item.filename, raw)
    route = route_document(text, item.filename, project_hint=project_hint)
    item = apply_route(item, route, text=text, set_routed=False)
    return save_item(_touch(item))


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

    if not can_dispatch(item.status):
        return {
            "ok": False,
            "status": "not_approved",
            "error": (f"Dispatch requires status 'approved'; current status is {item.status!r}"),
            "item_id": item_id,
            "item": item.to_dict(),
        }

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
        # Free-form work dispatch (ingestion task text). Guardian already
        # proceeded above — pass guardian_allowed so invoke_fleet_trigger
        # cannot be reached without that gate (write-path audit P0).
        arm = await invoke_fleet_trigger(
            "arm",
            project=project,
            caller="ingestion",
            action=guardian_action,
            guardian_allowed=True,
            guardian_status="allowed",
        )
        work = await invoke_fleet_trigger(
            f"work {task}",
            project=project,
            caller="ingestion",
            action=guardian_action,
            guardian_allowed=True,
            guardian_status="allowed",
        )
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
                f"Dispatched ingestion item to FirstMate on {project}. Task: {task[:120]}"
            )

    if result.get("ok"):
        try:
            item = _apply_status(item, "dispatched")
        except InvalidTransitionError as exc:
            return {
                "ok": False,
                "status": "invalid_transition",
                "error": str(exc),
                "item_id": item_id,
            }
        item.dispatch_result = {k: v for k, v in result.items() if k != "spoken"}
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
            1
            for i in items
            if i.status in ("approved", "needs_review", "routed") and i.dev_recommended
        ),
        "awaiting_approval": sum(1 for i in items if i.status == "needs_review"),
    }
