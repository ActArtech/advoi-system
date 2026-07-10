"""Unit tests for PWA home briefs surface (mirrors web/components/pwaBriefsSurface.ts).

Python port keeps CI green without a JS test runner. Keep copy/rules in sync.
Also covers thin GET /api/briefs (existing data layer, no frame run).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

HOME_BRIEFS_LIMIT = 5
OPEN_BRIEFS_FRAME_ID = "open_briefs"


def parse_open_briefs_payload(data: Any) -> dict[str, Any]:
    if data is None or not isinstance(data, dict):
        return {"briefs": [], "source": None, "count": 0}
    raw_list = data.get("briefs") if isinstance(data.get("briefs"), list) else []
    briefs: list[str] = []
    for item in raw_list:
        if isinstance(item, str):
            t = item.strip()
            if t:
                briefs.append(t)
        elif isinstance(item, dict):
            t = str(item.get("title") or "").strip()
            if t:
                briefs.append(t)
    count = data.get("count")
    if not isinstance(count, (int, float)):
        count = len(briefs)
    source = data.get("source")
    source_s = str(source).strip() if source is not None and str(source).strip() else None
    return {"briefs": briefs, "source": source_s, "count": int(count)}


def parse_review_queue_payload(data: Any) -> dict[str, Any]:
    if data is None or not isinstance(data, dict):
        return {"pending": [], "count": 0}
    raw_list = data.get("pending") if isinstance(data.get("pending"), list) else []
    pending: list[dict[str, Any]] = []
    for item in raw_list:
        if not isinstance(item, dict):
            continue
        try:
            queue_id = int(item.get("queue_id"))
        except (TypeError, ValueError):
            continue
        title = str(item.get("title") or "").strip()
        if not title:
            continue
        brief_url = item.get("brief_url")
        pending.append(
            {
                "queue_id": queue_id,
                "title": title,
                "status": str(item.get("status") or "pending"),
                "brief_url": str(brief_url).strip() if brief_url else None,
                "source_frame": (
                    str(item["source_frame"]) if item.get("source_frame") is not None else None
                ),
                "created_at": (
                    str(item["created_at"]) if item.get("created_at") is not None else None
                ),
            }
        )
    count = data.get("count")
    if not isinstance(count, (int, float)):
        count = len(pending)
    return {"pending": pending, "count": int(count)}


def open_briefs_section_model(
    *,
    briefs: list[str],
    loading: bool = False,
    error: bool = False,
    source: str | None = None,
    limit: int = HOME_BRIEFS_LIMIT,
) -> dict[str, Any]:
    base = {
        "id": "open_briefs",
        "title": "Open briefs",
        "empty_label": "No open briefs in memory.",
        "error_label": "Could not load open briefs.",
        "cta_label": "Hear open briefs",
        "frame_id": OPEN_BRIEFS_FRAME_ID,
    }
    if loading:
        return {**base, "state": "loading", "count": 0, "cards": []}
    if error:
        return {**base, "state": "error", "count": 0, "cards": []}
    titles = [t.strip() for t in briefs if t and str(t).strip()]
    cards = [
        {
            "key": f"open-{i}-{title[:24]}",
            "title": title,
            "kind": "open_brief",
            "status_label": "open",
            "href": None,
            "meta": f"source: {source}" if source else None,
        }
        for i, title in enumerate(titles[:limit])
    ]
    return {
        **base,
        "state": "empty" if not cards else "ok",
        "count": len(titles),
        "cards": cards,
    }


def review_queue_section_model(
    *,
    pending: list[dict[str, Any]],
    loading: bool = False,
    error: bool = False,
    limit: int = HOME_BRIEFS_LIMIT,
) -> dict[str, Any]:
    base = {
        "id": "review_queue",
        "title": "Review queue",
        "empty_label": "Review queue is clear.",
        "error_label": "Could not load review queue.",
        "cta_label": None,
        "frame_id": None,
    }
    if loading:
        return {**base, "state": "loading", "count": 0, "cards": []}
    if error:
        return {**base, "state": "error", "count": 0, "cards": []}
    cards = []
    for item in pending[:limit]:
        queue_id = item["queue_id"]
        href = item.get("brief_url") or f"/briefs/{queue_id}"
        cards.append(
            {
                "key": f"review-{queue_id}",
                "title": item["title"],
                "kind": "review",
                "status_label": item.get("status") or "pending",
                "href": href,
                "meta": f"queued {item['created_at']}" if item.get("created_at") else None,
            }
        )
    return {
        **base,
        "state": "empty" if not cards else "ok",
        "count": len(pending),
        "cards": cards,
    }


def home_briefs_surface_model(
    *,
    open_briefs: list[str],
    review_pending: list[dict[str, Any]],
    open_loading: bool = False,
    open_error: bool = False,
    review_loading: bool = False,
    review_error: bool = False,
    open_source: str | None = None,
    limit: int = HOME_BRIEFS_LIMIT,
) -> dict[str, Any]:
    open_sec = open_briefs_section_model(
        briefs=open_briefs,
        loading=open_loading,
        error=open_error,
        source=open_source,
        limit=limit,
    )
    review_sec = review_queue_section_model(
        pending=review_pending,
        loading=review_loading,
        error=review_error,
        limit=limit,
    )
    return {
        "open_briefs": open_sec,
        "review_queue": review_sec,
        "has_any_cards": bool(open_sec["cards"] or review_sec["cards"]),
        "eyebrow": "Decisions · home",
        "heading": "Open briefs & review",
    }


# --- pure model tests (mock data render) ---


def test_parse_open_briefs_payload_titles():
    parsed = parse_open_briefs_payload(
        {"briefs": ["  Staging catch-up ", "Voice launch", ""], "count": 2, "source": "postgres"}
    )
    assert parsed["briefs"] == ["Staging catch-up", "Voice launch"]
    assert parsed["source"] == "postgres"
    assert parsed["count"] == 2


def test_parse_open_briefs_payload_object_titles():
    parsed = parse_open_briefs_payload({"briefs": [{"title": "Alpha"}, {"title": ""}]})
    assert parsed["briefs"] == ["Alpha"]


def test_parse_open_briefs_payload_bad_input():
    assert parse_open_briefs_payload(None)["briefs"] == []
    assert parse_open_briefs_payload("x")["briefs"] == []


def test_parse_review_queue_payload_items():
    parsed = parse_review_queue_payload(
        {
            "pending": [
                {
                    "queue_id": 12,
                    "title": "Deep review A",
                    "status": "pending",
                    "brief_url": "https://advoi.keyteller.com/briefs/12",
                },
                {"queue_id": "bad", "title": "skip"},
                {"queue_id": 3, "title": "  "},
            ],
            "count": 1,
        }
    )
    assert len(parsed["pending"]) == 1
    assert parsed["pending"][0]["queue_id"] == 12
    assert parsed["pending"][0]["brief_url"].endswith("/briefs/12")


def test_open_briefs_section_renders_cards_from_mock():
    m = open_briefs_section_model(
        briefs=["ADVoi voice launch", "Staging catch-up", "Fleet governance"],
        source="postgres",
    )
    assert m["state"] == "ok"
    assert m["count"] == 3
    assert len(m["cards"]) == 3
    assert m["cards"][0]["title"] == "ADVoi voice launch"
    assert m["cards"][0]["kind"] == "open_brief"
    assert m["cards"][0]["href"] is None
    assert m["frame_id"] == OPEN_BRIEFS_FRAME_ID
    assert m["cta_label"] == "Hear open briefs"


def test_open_briefs_section_empty_and_error():
    empty = open_briefs_section_model(briefs=[])
    assert empty["state"] == "empty"
    assert empty["empty_label"] == "No open briefs in memory."
    err = open_briefs_section_model(briefs=[], error=True)
    assert err["state"] == "error"
    loading = open_briefs_section_model(briefs=[], loading=True)
    assert loading["state"] == "loading"


def test_open_briefs_section_respects_limit():
    titles = [f"Brief {i}" for i in range(10)]
    m = open_briefs_section_model(briefs=titles, limit=HOME_BRIEFS_LIMIT)
    assert m["count"] == 10
    assert len(m["cards"]) == HOME_BRIEFS_LIMIT


def test_review_queue_section_renders_cards_with_links():
    pending = [
        {
            "queue_id": 7,
            "title": "Queue item",
            "status": "pending",
            "brief_url": "https://advoi.keyteller.com/briefs/7",
            "created_at": "2026-07-10T12:00:00+00:00",
        },
        {
            "queue_id": 8,
            "title": "No url item",
            "status": "pending",
            "brief_url": None,
        },
    ]
    m = review_queue_section_model(pending=pending)
    assert m["state"] == "ok"
    assert m["count"] == 2
    assert m["cards"][0]["href"] == "https://advoi.keyteller.com/briefs/7"
    assert m["cards"][1]["href"] == "/briefs/8"
    assert m["cards"][0]["kind"] == "review"
    assert "queued" in (m["cards"][0]["meta"] or "")


def test_review_queue_section_empty():
    m = review_queue_section_model(pending=[])
    assert m["state"] == "empty"
    assert m["empty_label"] == "Review queue is clear."


def test_home_surface_model_with_mock_data():
    m = home_briefs_surface_model(
        open_briefs=["Alpha brief"],
        review_pending=[
            {
                "queue_id": 1,
                "title": "Review me",
                "status": "pending",
                "brief_url": "https://example.com/briefs/1",
            }
        ],
        open_source="postgres",
    )
    assert m["has_any_cards"] is True
    assert m["eyebrow"] == "Decisions · home"
    assert m["heading"] == "Open briefs & review"
    assert m["open_briefs"]["cards"][0]["title"] == "Alpha brief"
    assert m["review_queue"]["cards"][0]["title"] == "Review me"


def test_home_surface_model_both_empty():
    m = home_briefs_surface_model(open_briefs=[], review_pending=[])
    assert m["has_any_cards"] is False
    assert m["open_briefs"]["state"] == "empty"
    assert m["review_queue"]["state"] == "empty"


def test_constants_stable():
    assert HOME_BRIEFS_LIMIT == 5
    assert OPEN_BRIEFS_FRAME_ID == "open_briefs"


# --- API thin wrapper ---


def test_api_briefs_lists_open(client):
    with patch(
        "advoi.routing.frame_runner._load_open_briefs",
        AsyncMock(return_value=(["Staging catch-up", "Voice launch"], "postgres")),
    ):
        resp = client.get("/api/briefs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 2
    assert data["briefs"] == ["Staging catch-up", "Voice launch"]
    assert data["source"] == "postgres"


def test_api_briefs_empty_when_unavailable(client):
    with patch(
        "advoi.routing.frame_runner._load_open_briefs",
        AsyncMock(return_value=([], "unavailable")),
    ):
        resp = client.get("/api/briefs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["briefs"] == []
    assert data["count"] == 0
    assert data["source"] == "unavailable"
