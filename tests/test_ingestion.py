"""Ingestion pipeline — upload, route, lifecycle-aware dispatch."""

import pytest

from advoi.ingestion.models import IngestItem
from advoi.ingestion.parse import extract_text
from advoi.ingestion.pipeline import (
    approve_item,
    dispatch_item_dev,
    ingest_upload,
    ingestion_summary,
    mark_needs_review,
    triage_item,
)
from advoi.ingestion.route import route_document
from advoi.ingestion.store import (
    _item_from_dict,
    get_item,
    list_items,
    save_item,
)


@pytest.fixture
def ingest_tmp(monkeypatch, tmp_path):
    root = tmp_path / "ingestion"
    monkeypatch.setenv("ADVOI_INGESTION_PATH", str(root))
    monkeypatch.setenv("ADVOI_FLEET_MOCK", "true")
    return root


def test_extract_text_md():
    text = extract_text("notes.md", b"# Fix clapart login\n\nUrgent bug in auth flow.")
    assert "clapart" in text


def test_route_clapart_dev(ingest_tmp):
    route = route_document(
        "Fix login bug on clapart staging urgently",
        "clapart-bug.md",
    )
    assert route["project_slug"] == "clapart"
    assert route["dev_recommended"] is True
    assert route["priority"] == "high"


def test_route_project_hint(ingest_tmp):
    route = route_document("generic notes", "x.md", project_hint="advoi")
    assert route["project_slug"] == "advoi"
    assert route["route_confidence"] == 1.0


@pytest.mark.asyncio
async def test_ingest_upload_and_list(ingest_tmp):
    item = await ingest_upload(
        "feature-clapart.md",
        b"Implement new TTS feature for clapart voice path.",
    )
    assert item.status == "uploaded"
    assert item.project_slug == "clapart"
    assert item.dev_recommended is True
    assert len(list_items()) == 1
    assert get_item(item.id) is not None


async def _approve_for_dispatch(item_id: str):
    await triage_item(item_id)
    await mark_needs_review(item_id)
    return await approve_item(item_id)


@pytest.mark.asyncio
async def test_dispatch_requires_confirm(ingest_tmp):
    item = await ingest_upload("task.md", b"Build API endpoint for advoi.")
    await _approve_for_dispatch(item.id)
    result = await dispatch_item_dev(item.id, confirmed=False)
    assert result["status"] == "confirmation_required"


@pytest.mark.asyncio
async def test_dispatch_dev_mock(ingest_tmp):
    item = await ingest_upload("task.md", b"Fix bug in clapart checkout flow.")
    await _approve_for_dispatch(item.id)
    result = await dispatch_item_dev(item.id, confirmed=True)
    assert result["ok"] is True
    updated = get_item(item.id)
    assert updated is not None
    assert updated.status == "dispatched"


@pytest.mark.asyncio
async def test_ingestion_api_upload(client, ingest_tmp, monkeypatch):
    monkeypatch.setenv("ADVOI_INGESTION_PATH", str(ingest_tmp))
    files = {"file": ("clapart.md", b"Ship clapart redirect fix", "text/markdown")}
    resp = client.post("/api/ingestion/upload", files=files, data={"project_hint": "clapart"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["item"]["project_slug"] == "clapart"
    assert data["item"]["status"] == "uploaded"
    assert "dispatch" not in data


def test_paperclip_ticket_id_model_roundtrip(ingest_tmp):
    item = IngestItem(
        id="abc123",
        filename="ticket.md",
        paperclip_ticket_id="pc-ticket-42",
        created_at=1.0,
        updated_at=1.0,
    )
    saved = save_item(item)
    assert saved.paperclip_ticket_id == "pc-ticket-42"
    loaded = get_item("abc123")
    assert loaded is not None
    assert loaded.paperclip_ticket_id == "pc-ticket-42"
    assert loaded.to_dict()["paperclip_ticket_id"] == "pc-ticket-42"
    # _item_from_dict preserves field from raw dict (including None default)
    from_raw = _item_from_dict(
        {"id": "x1", "filename": "a.md", "paperclip_ticket_id": "pc-99"}
    )
    assert from_raw.paperclip_ticket_id == "pc-99"
    bare = _item_from_dict({"id": "x2", "filename": "b.md"})
    assert bare.paperclip_ticket_id is None


@pytest.mark.asyncio
async def test_ingest_upload_paperclip_ticket_id(ingest_tmp):
    item = await ingest_upload(
        "linked.md",
        b"Implement paperclip bridge for clapart.",
        paperclip_ticket_id="pc-ticket-77",
    )
    assert item.paperclip_ticket_id == "pc-ticket-77"
    stored = get_item(item.id)
    assert stored is not None
    assert stored.paperclip_ticket_id == "pc-ticket-77"


@pytest.mark.asyncio
async def test_ingestion_api_upload_paperclip_ticket_id(client, ingest_tmp, monkeypatch):
    monkeypatch.setenv("ADVOI_INGESTION_PATH", str(ingest_tmp))
    ticket_id = "pc-ticket-api-01"
    files = {"file": ("clapart.md", b"Ship clapart redirect fix", "text/markdown")}
    resp = client.post(
        "/api/ingestion/upload",
        files=files,
        data={"project_hint": "clapart", "paperclip_ticket_id": ticket_id},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["item"]["paperclip_ticket_id"] == ticket_id
    item_id = data["item"]["id"]

    get_resp = client.get(f"/api/ingestion/items/{item_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["paperclip_ticket_id"] == ticket_id

    list_resp = client.get("/api/ingestion/items")
    assert list_resp.status_code == 200
    listed = list_resp.json()["items"]
    match = next(i for i in listed if i["id"] == item_id)
    assert match["paperclip_ticket_id"] == ticket_id


def test_ingestion_summary_empty(ingest_tmp):
    assert ingestion_summary()["total"] == 0


def test_unsupported_file(ingest_tmp):
    with pytest.raises(ValueError, match="Unsupported"):
        extract_text("photo.bin", b"\x00\x01")
