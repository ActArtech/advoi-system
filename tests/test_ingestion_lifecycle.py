"""T0: ingestion lifecycle state machine (M7.2–M7.3 / moat R4)."""

from __future__ import annotations

import pytest

from advoi.ingestion.lifecycle import (
    ALLOWED_TRANSITIONS,
    HAPPY_PATH,
    InvalidTransitionError,
    can_dispatch,
    can_transition,
    transition,
)
from advoi.ingestion.pipeline import (
    approve_item,
    dispatch_item_dev,
    ingest_upload,
    mark_needs_review,
    triage_item,
)
from advoi.ingestion.store import get_item


@pytest.fixture
def ingest_tmp(monkeypatch, tmp_path):
    root = tmp_path / "ingestion"
    monkeypatch.setenv("ADVOI_INGESTION_PATH", str(root))
    monkeypatch.setenv("ADVOI_FLEET_MOCK", "true")
    return root


def test_happy_path_order():
    assert HAPPY_PATH == (
        "uploaded",
        "triaged",
        "needs_review",
        "approved",
        "dispatched",
    )


def test_allowed_forward_transitions():
    assert can_transition("uploaded", "triaged")
    assert can_transition("triaged", "needs_review")
    assert can_transition("needs_review", "approved")
    assert can_transition("approved", "dispatched")
    assert can_transition("uploaded", "failed")


def test_reject_illegal_transitions():
    assert not can_transition("uploaded", "approved")
    assert not can_transition("uploaded", "dispatched")
    assert not can_transition("triaged", "approved")
    assert not can_transition("needs_review", "dispatched")
    assert not can_transition("dispatched", "approved")
    assert not can_transition("failed", "uploaded")
    with pytest.raises(InvalidTransitionError):
        transition("uploaded", "dispatched")


def test_can_dispatch_only_approved():
    assert can_dispatch("approved") is True
    for status in ("uploaded", "triaged", "needs_review", "routed", "dispatched", "failed"):
        assert can_dispatch(status) is False


def test_allowed_transitions_cover_statuses():
    expected = {
        "uploaded",
        "triaged",
        "needs_review",
        "routed",
        "approved",
        "dispatched",
        "failed",
    }
    assert set(ALLOWED_TRANSITIONS) == expected


@pytest.mark.asyncio
async def test_upload_stays_uploaded(ingest_tmp):
    item = await ingest_upload(
        "feature-clapart.md",
        b"Implement new TTS feature for clapart voice path.",
    )
    assert item.status == "uploaded"
    assert item.project_slug == "clapart"
    assert item.dev_recommended is True


@pytest.mark.asyncio
async def test_full_happy_path_transitions(ingest_tmp):
    item = await ingest_upload("task.md", b"Fix bug in clapart checkout flow.")
    assert item.status == "uploaded"

    item = await triage_item(item.id)
    assert item.status == "triaged"

    item = await mark_needs_review(item.id)
    assert item.status == "needs_review"

    item = await approve_item(item.id)
    assert item.status == "approved"

    result = await dispatch_item_dev(item.id, confirmed=True)
    assert result["ok"] is True
    updated = get_item(item.id)
    assert updated is not None
    assert updated.status == "dispatched"


@pytest.mark.asyncio
async def test_reject_dispatch_from_non_approved_states(ingest_tmp):
    item = await ingest_upload("task.md", b"Build API endpoint for advoi.")
    assert item.status == "uploaded"

    for advance in (
        None,
        "triage",
        "needs_review",
    ):
        if advance == "triage":
            item = await triage_item(item.id)
        elif advance == "needs_review":
            item = await mark_needs_review(item.id)

        result = await dispatch_item_dev(item.id, confirmed=True)
        assert result["ok"] is False
        assert result["status"] == "not_approved"
        persisted = get_item(item.id)
        assert persisted is not None
        assert persisted.status != "dispatched"


@pytest.mark.asyncio
async def test_reject_skip_to_approve(ingest_tmp):
    item = await ingest_upload("notes.md", b"Ship clapart redirect fix.")
    with pytest.raises(InvalidTransitionError):
        await approve_item(item.id)
    assert get_item(item.id).status == "uploaded"


@pytest.mark.asyncio
async def test_dispatch_requires_confirm_when_approved(ingest_tmp):
    item = await ingest_upload("task.md", b"Build API endpoint for advoi.")
    item = await triage_item(item.id)
    item = await mark_needs_review(item.id)
    item = await approve_item(item.id)
    result = await dispatch_item_dev(item.id, confirmed=False)
    assert result["status"] == "confirmation_required"
    assert get_item(item.id).status == "approved"


@pytest.mark.asyncio
async def test_lifecycle_api_endpoints(client, ingest_tmp, monkeypatch):
    monkeypatch.setenv("ADVOI_INGESTION_PATH", str(ingest_tmp))
    files = {"file": ("clapart.md", b"Ship clapart redirect fix", "text/markdown")}
    resp = client.post(
        "/api/ingestion/upload",
        files=files,
        data={"project_hint": "clapart"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["item"]["status"] == "uploaded"
    assert "dispatch" not in data
    item_id = data["item"]["id"]

    # Reject dispatch before approve
    bad = client.post(
        f"/api/ingestion/items/{item_id}/dispatch-dev",
        json={"confirmed": True},
    )
    assert bad.status_code == 409

    assert client.post(f"/api/ingestion/items/{item_id}/triage").status_code == 200
    assert (
        client.post(f"/api/ingestion/items/{item_id}/needs-review").json()["item"]["status"]
        == "needs_review"
    )
    assert (
        client.post(f"/api/ingestion/items/{item_id}/approve").json()["item"]["status"]
        == "approved"
    )

    good = client.post(
        f"/api/ingestion/items/{item_id}/dispatch-dev",
        json={"confirmed": True},
    )
    assert good.status_code == 200
    body = good.json()
    assert body["ok"] is True
    assert body["item"]["status"] == "dispatched"
