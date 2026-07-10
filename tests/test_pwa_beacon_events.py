"""T0: PWA thin beacon → POST /api/events → portfolio_events (PEL).

Ship: advoi-analytics-pwa-beacon-01
Event types: pwa_connect, frame_tap, confirm_shown, confirm_accept, error
"""

from __future__ import annotations

import pytest

from advoi.analytics.pel import (
    EventType,
    PWA_BEACON_EVENT_TYPES,
    memory_rows,
    reset_memory_store,
)


@pytest.fixture(autouse=True)
def _pel_memory(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ADVOI_PEL_MEMORY", "true")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    reset_memory_store()
    yield
    reset_memory_store()


BEACON_TYPES = (
    "pwa_connect",
    "frame_tap",
    "confirm_shown",
    "confirm_accept",
    "error",
)


def test_pwa_beacon_types_in_event_type_enum():
    values = {t.value for t in EventType}
    for name in BEACON_TYPES:
        assert name in values, f"EventType missing {name}"
    assert PWA_BEACON_EVENT_TYPES == frozenset(BEACON_TYPES)


@pytest.mark.parametrize("event_type", BEACON_TYPES)
def test_post_api_events_inserts_pel_row(client, event_type: str):
    resp = client.post(
        "/api/events",
        json={
            "type": event_type,
            "venture_id": "advoi",
            "session_id": "pwa-test-session",
            "payload": {"ui_event": "unit", "frame_id": "fleet_status"},
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ok"] is True
    assert body["type"] == event_type
    assert body["persisted"] is True
    assert body["id"]

    rows = memory_rows()
    assert len(rows) == 1
    row = rows[0]
    assert row["id"] == body["id"]
    assert row["venture_id"] == "advoi"
    assert row["source"] == "api"
    assert row["type"] == event_type
    assert row["payload"]["client"] == "pwa"
    assert row["payload"]["session_id"] == "pwa-test-session"
    assert row["payload"]["frame_id"] == "fleet_status"
    # Schema columns present
    for col in (
        "id",
        "timestamp",
        "venture_id",
        "source",
        "type",
        "payload",
        "guardian_status",
        "execution_ref",
        "trace_id",
        "created_at",
    ):
        assert col in row


def test_post_api_events_confirm_shown_sets_guardian_pending(client):
    resp = client.post(
        "/api/events",
        json={"type": "confirm_shown", "payload": {"frame_id": "queue_deep_review"}},
    )
    assert resp.status_code == 200
    row = memory_rows()[0]
    assert row["type"] == "confirm_shown"
    assert row["guardian_status"] == "pending"


def test_post_api_events_confirm_accept_sets_guardian_allowed(client):
    resp = client.post(
        "/api/events",
        json={"type": "confirm_accept", "payload": {"frame_id": "queue_deep_review"}},
    )
    assert resp.status_code == 200
    row = memory_rows()[0]
    assert row["type"] == "confirm_accept"
    assert row["guardian_status"] == "allowed"


def test_post_api_events_rejects_unknown_type(client):
    resp = client.post(
        "/api/events",
        json={"type": "page_view", "payload": {}},
    )
    assert resp.status_code == 422
    assert memory_rows() == []


def test_post_api_events_rejects_frame_run_via_beacon(client):
    """Server-side frame_run is not a client beacon type."""
    resp = client.post("/api/events", json={"type": "frame_run", "payload": {}})
    assert resp.status_code == 422
    assert memory_rows() == []


def test_post_api_events_all_five_types_distinct_rows(client):
    for event_type in BEACON_TYPES:
        resp = client.post(
            "/api/events",
            json={
                "type": event_type,
                "session_id": "batch-session",
                "payload": {"n": event_type},
            },
        )
        assert resp.status_code == 200, event_type
    rows = memory_rows()
    assert len(rows) == 5
    types = {r["type"] for r in rows}
    assert types == set(BEACON_TYPES)


def test_beacon_type_from_ui_event_mapping():
    """Python mirror of web/components/pwaBeacon.ts beaconTypeFromUiEvent."""
    mapping = {
        "CONNECT_OK": "pwa_connect",
        "FRAME_START": "frame_tap",
        "CONFIRMATION_REQUIRED": "confirm_shown",
        "CONNECT_FAIL": "error",
        "ERROR": "error",
        "FRAME_OK": None,
        "DISCONNECT": None,
        "CONNECT_START": None,
        "FRAME_FAIL_KEEP_VOICE": None,
        "RESET_IDLE": None,
    }

    def beacon_type_from_ui_event(event_type: str) -> str | None:
        return {
            "CONNECT_OK": "pwa_connect",
            "FRAME_START": "frame_tap",
            "CONFIRMATION_REQUIRED": "confirm_shown",
            "CONNECT_FAIL": "error",
            "ERROR": "error",
        }.get(event_type)

    for ui_event, expected in mapping.items():
        assert beacon_type_from_ui_event(ui_event) == expected
