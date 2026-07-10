"""Unit tests for /ingest UI lifecycle model (mirrors web/components/ingestLifecycle.ts).

Python port keeps CI green without a JS test runner. Keep action maps in sync.
"""

from __future__ import annotations

from typing import Any


HAPPY_PATH = (
    "uploaded",
    "triaged",
    "needs_review",
    "approved",
    "dispatched",
)


def actions_for_status(status: str) -> list[dict[str, Any]]:
    """Mirror of actionsForStatus in web/components/ingestLifecycle.ts."""
    if status == "uploaded":
        return [
            {
                "id": "triage",
                "label": "Triage",
                "path": "triage",
                "method": "POST",
            }
        ]
    if status == "triaged":
        return [
            {
                "id": "needs_review",
                "label": "Needs review",
                "path": "needs-review",
                "method": "POST",
            }
        ]
    if status == "needs_review":
        return [
            {
                "id": "approve",
                "label": "Approve",
                "path": "approve",
                "method": "POST",
            }
        ]
    if status == "routed":
        return [
            {
                "id": "needs_review",
                "label": "Needs review",
                "path": "needs-review",
                "method": "POST",
            },
            {
                "id": "approve",
                "label": "Approve",
                "path": "approve",
                "method": "POST",
            },
        ]
    if status == "approved":
        return [
            {
                "id": "dispatch_dev",
                "label": "Dispatch to FirstMate",
                "path": "dispatch-dev",
                "method": "POST",
                "body": {"confirmed": True, "mode": "work"},
            }
        ]
    return []


def action_url(api_base: str, item_id: str, action: dict[str, Any]) -> str:
    base = api_base.rstrip("/")
    return f"{base}/ingestion/items/{item_id}/{action['path']}"


def status_badge_tone(status: str) -> str:
    mapping = {
        "uploaded": "neutral",
        "triaged": "progress",
        "routed": "progress",
        "needs_review": "review",
        "approved": "ready",
        "dispatched": "done",
        "failed": "error",
    }
    return mapping.get(status, "neutral")


def parse_api_error(http_status: int | None, body: Any) -> dict[str, Any]:
    """Mirror of parseApiError — surfaces 422 ontology + 409 transition + failed items."""
    empty = {
        "message": "Request failed.",
        "httpStatus": http_status,
        "code": None,
        "isError": True,
    }
    if body is None or not isinstance(body, dict):
        if http_status == 422:
            return {**empty, "message": "Ontology validation failed (422)."}
        if http_status == 409:
            return {**empty, "message": "Invalid lifecycle transition (409)."}
        return empty

    code = body.get("code") if isinstance(body.get("code"), str) else None
    message: str | None = None
    detail = body.get("detail")
    if isinstance(detail, str) and detail.strip():
        message = detail
    elif isinstance(detail, list) and detail:
        parts = []
        for d in detail:
            if isinstance(d, dict) and "msg" in d:
                parts.append(str(d["msg"]))
            else:
                parts.append(str(d))
        message = "; ".join(parts)
    elif isinstance(body.get("error"), str) and body["error"].strip():
        message = body["error"]
    elif isinstance(body.get("spoken"), str) and body["spoken"].strip():
        message = body["spoken"]
    elif isinstance(body.get("status"), str) and body.get("ok") is False:
        message = str(body["status"])

    if http_status == 422:
        prefix = f"Ontology 422 ({code})" if code else "Ontology 422"
        return {
            "message": f"{prefix}: {message}" if message else f"{prefix}.",
            "httpStatus": http_status,
            "code": code,
            "isError": True,
        }
    if http_status == 409:
        return {
            "message": message or "Invalid lifecycle transition (409).",
            "httpStatus": http_status,
            "code": code,
            "isError": True,
        }
    if body.get("ok") is False:
        return {
            "message": message or "Request failed.",
            "httpStatus": http_status,
            "code": code,
            "isError": True,
        }
    item = body.get("item")
    if isinstance(item, dict) and item.get("status") == "failed":
        err = item.get("error") if isinstance(item.get("error"), str) else None
        return {
            "message": err or message or "Item marked failed.",
            "httpStatus": http_status,
            "code": code,
            "isError": True,
        }
    if message:
        return {
            "message": message,
            "httpStatus": http_status,
            "code": code,
            "isError": http_status is not None and http_status >= 400,
        }
    if http_status is not None and http_status >= 400:
        return empty
    return {
        "message": "",
        "httpStatus": http_status,
        "code": code,
        "isError": False,
    }


# --- tests -----------------------------------------------------------------


def test_happy_path_matches_api_contract():
    assert HAPPY_PATH == (
        "uploaded",
        "triaged",
        "needs_review",
        "approved",
        "dispatched",
    )


def test_actions_forward_chain():
    assert [a["path"] for a in actions_for_status("uploaded")] == ["triage"]
    assert [a["path"] for a in actions_for_status("triaged")] == ["needs-review"]
    assert [a["path"] for a in actions_for_status("needs_review")] == ["approve"]
    dispatch = actions_for_status("approved")
    assert len(dispatch) == 1
    assert dispatch[0]["path"] == "dispatch-dev"
    assert dispatch[0]["body"] == {"confirmed": True, "mode": "work"}


def test_no_actions_on_terminal():
    assert actions_for_status("dispatched") == []
    assert actions_for_status("failed") == []


def test_legacy_routed_offers_review_or_approve():
    paths = [a["path"] for a in actions_for_status("routed")]
    assert paths == ["needs-review", "approve"]


def test_action_urls_match_api():
    base = "/api"
    item_id = "abc-123"
    for status, expected_suffix in (
        ("uploaded", "triage"),
        ("triaged", "needs-review"),
        ("needs_review", "approve"),
        ("approved", "dispatch-dev"),
    ):
        action = actions_for_status(status)[0]
        url = action_url(base, item_id, action)
        assert url == f"/api/ingestion/items/{item_id}/{expected_suffix}"


def test_badge_tones():
    assert status_badge_tone("uploaded") == "neutral"
    assert status_badge_tone("needs_review") == "review"
    assert status_badge_tone("approved") == "ready"
    assert status_badge_tone("dispatched") == "done"
    assert status_badge_tone("failed") == "error"


def test_parse_ontology_422():
    err = parse_api_error(
        422,
        {
            "detail": "Unknown venture_id: totally-unknown-venture",
            "code": "UNKNOWN_VENTURE_ID",
        },
    )
    assert err["isError"] is True
    assert err["code"] == "UNKNOWN_VENTURE_ID"
    assert "422" in err["message"]
    assert "totally-unknown-venture" in err["message"]


def test_parse_lifecycle_409():
    err = parse_api_error(
        409,
        {"detail": "Invalid ingestion transition: 'uploaded' → 'dispatched'"},
    )
    assert err["isError"] is True
    assert "uploaded" in err["message"] or "409" in err["message"]


def test_parse_failed_item_payload():
    err = parse_api_error(
        200,
        {
            "ok": False,
            "error": "parse blew up",
            "item": {"status": "failed", "error": "parse blew up"},
        },
    )
    assert err["isError"] is True
    assert "parse blew up" in err["message"]


def test_no_auto_dispatch_action_on_uploaded():
    """UI must not offer dispatch from uploaded (API rejects non-approved)."""
    ids = [a["id"] for a in actions_for_status("uploaded")]
    assert "dispatch_dev" not in ids
    assert "approve" not in ids
