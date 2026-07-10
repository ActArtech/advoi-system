"""T0: M7.2 keyword triage classifier + triaged/needs_review transitions."""

from __future__ import annotations

import pytest

from advoi.ingestion.models import IngestItem
from advoi.ingestion.pipeline import ingest_upload, triage_item
from advoi.ingestion.store import get_item
from advoi.ingestion.triage import (
    LOW_ROUTE_CONFIDENCE,
    classify_from_signals,
    classify_item,
)


@pytest.fixture
def ingest_tmp(monkeypatch, tmp_path):
    root = tmp_path / "ingestion"
    monkeypatch.setenv("ADVOI_INGESTION_PATH", str(root))
    monkeypatch.setenv("ADVOI_FLEET_MOCK", "true")
    return root


def test_classifier_clear_route_targets_triaged():
    result = classify_from_signals(
        route_confidence=0.9,
        priority="medium",
        priority_score=60,
        dev_recommended=True,
        project_slug="clapart",
        venture_id="firstmate-fleet",
        content_preview="Implement TTS feature for the clapart voice path this week.",
        filename="feature.md",
    )
    assert result.target_status == "triaged"
    assert result.score > 0.5
    assert "high_confidence" in result.labels
    assert "has_project" in result.labels
    assert "urgent" not in result.labels


def test_classifier_low_confidence_needs_review():
    result = classify_from_signals(
        route_confidence=0.2,
        priority="low",
        priority_score=35,
        project_slug="clapart",
        content_preview="Some generic notes about process improvements and follow-ups.",
        filename="notes.md",
    )
    assert result.target_status == "needs_review"
    assert "low_confidence" in result.labels
    assert any("below threshold" in r for r in result.reasons)
    assert result.signals["low_route_threshold"] == LOW_ROUTE_CONFIDENCE


def test_classifier_missing_project_needs_review():
    result = classify_from_signals(
        route_confidence=0.9,
        priority="medium",
        priority_score=50,
        project_slug=None,
        content_preview="A reasonably long note without a clear fleet project assignment.",
        filename="orphan.md",
    )
    assert result.target_status == "needs_review"
    assert "missing_project" in result.labels


def test_classifier_urgent_keywords_needs_review():
    result = classify_from_signals(
        route_confidence=0.95,
        priority="high",
        priority_score=85,
        project_slug="clapart",
        content_preview="Urgent P0: production down on checkout — fix blocker ASAP.",
        filename="incident.md",
    )
    assert result.target_status == "needs_review"
    assert "urgent" in result.labels


def test_classifier_review_keywords_needs_review():
    result = classify_from_signals(
        route_confidence=0.85,
        priority="medium",
        priority_score=50,
        project_slug="advoi",
        content_preview="Please review this legal compliance memo before sign-off.",
        filename="legal.md",
    )
    assert result.target_status == "needs_review"
    assert "review_flag" in result.labels


def test_classifier_thin_content_needs_review():
    result = classify_from_signals(
        route_confidence=0.9,
        priority="medium",
        priority_score=50,
        project_slug="advoi",
        content_preview="short",
        filename="x.md",
    )
    assert result.target_status == "needs_review"
    assert "thin_content" in result.labels


def test_classifier_ambiguous_keywords_needs_review():
    result = classify_from_signals(
        route_confidence=0.8,
        priority="medium",
        priority_score=50,
        project_slug="hermes",
        content_preview="TODO: TBD unclear ownership for this WIP placeholder item.",
        filename="wip.md",
    )
    assert result.target_status == "needs_review"
    assert "ambiguous" in result.labels


def test_classify_item_uses_model_fields():
    item = IngestItem(
        id="t1",
        filename="ok.md",
        project_slug="advoi",
        route_confidence=0.85,
        priority="medium",
        priority_score=60,
        content_preview="Ship documentation updates for the advoi voice path this sprint.",
        summary="Ship documentation updates",
    )
    result = classify_item(item)
    assert result.target_status == "triaged"
    assert result.to_dict()["target_status"] == "triaged"


@pytest.mark.asyncio
async def test_triage_item_clear_content_stays_triaged(ingest_tmp):
    """Clear medium-priority dev note → triaged (not auto needs_review)."""
    item = await ingest_upload(
        "feature-clapart.md",
        b"Implement new TTS feature for clapart voice path this sprint.",
        project_hint="clapart",
    )
    assert item.status == "uploaded"

    item = await triage_item(item.id)
    assert item.status == "triaged"
    assert item.extra.get("triage", {}).get("target_status") == "triaged"
    stored = get_item(item.id)
    assert stored is not None
    assert stored.status == "triaged"
    assert "triage" in stored.extra


@pytest.mark.asyncio
async def test_triage_item_urgent_advances_to_needs_review(ingest_tmp):
    item = await ingest_upload(
        "incident.md",
        b"Urgent P0 production down on clapart checkout - critical blocker ASAP.",
        project_hint="clapart",
    )
    assert item.status == "uploaded"

    item = await triage_item(item.id)
    assert item.status == "needs_review"
    triage = item.extra.get("triage") or {}
    assert triage.get("target_status") == "needs_review"
    assert "urgent" in triage.get("labels", [])


@pytest.mark.asyncio
async def test_triage_item_without_classifier_stops_at_triaged(ingest_tmp):
    item = await ingest_upload(
        "incident.md",
        b"Urgent P0 production down on clapart checkout - critical blocker ASAP.",
        project_hint="clapart",
    )
    item = await triage_item(item.id, apply_classifier=False)
    assert item.status == "triaged"
    assert "triage" not in (item.extra or {})


@pytest.mark.asyncio
async def test_auto_triage_on_upload_default_off(ingest_tmp):
    item = await ingest_upload(
        "feature.md",
        b"Implement new TTS feature for clapart voice path this sprint.",
        project_hint="clapart",
    )
    assert item.status == "uploaded"


@pytest.mark.asyncio
async def test_auto_triage_on_upload_clear(ingest_tmp):
    item = await ingest_upload(
        "feature.md",
        b"Implement new TTS feature for clapart voice path this sprint.",
        project_hint="clapart",
        auto_triage=True,
    )
    assert item.status == "triaged"
    assert item.extra.get("triage", {}).get("target_status") == "triaged"


@pytest.mark.asyncio
async def test_auto_triage_on_upload_urgent_needs_review(ingest_tmp):
    item = await ingest_upload(
        "incident.md",
        b"Urgent P0 production down on clapart checkout - critical blocker ASAP.",
        project_hint="clapart",
        auto_triage=True,
    )
    assert item.status == "needs_review"


@pytest.mark.asyncio
async def test_api_auto_triage_form_flag(client, ingest_tmp, monkeypatch):
    monkeypatch.setenv("ADVOI_INGESTION_PATH", str(ingest_tmp))
    files = {
        "file": (
            "incident.md",
            b"Urgent P0 production down on clapart - critical blocker ASAP.",
            "text/markdown",
        )
    }
    resp = client.post(
        "/api/ingestion/upload",
        files=files,
        data={"project_hint": "clapart", "auto_triage": "true"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["item"]["status"] == "needs_review"
    assert body["item"]["extra"]["triage"]["target_status"] == "needs_review"


@pytest.mark.asyncio
async def test_api_triage_endpoint_writes_classifier(client, ingest_tmp, monkeypatch):
    monkeypatch.setenv("ADVOI_INGESTION_PATH", str(ingest_tmp))
    files = {
        "file": (
            "feature.md",
            b"Implement documentation updates for the advoi voice path this sprint.",
            "text/markdown",
        )
    }
    up = client.post(
        "/api/ingestion/upload",
        files=files,
        data={"project_hint": "advoi"},
    )
    assert up.status_code == 200
    item_id = up.json()["item"]["id"]
    assert up.json()["item"]["status"] == "uploaded"

    tri = client.post(f"/api/ingestion/items/{item_id}/triage")
    assert tri.status_code == 200
    item = tri.json()["item"]
    assert item["status"] == "triaged"
    assert item["extra"]["triage"]["target_status"] == "triaged"
