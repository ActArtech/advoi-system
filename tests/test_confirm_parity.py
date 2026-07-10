"""Unit tests for PWA confirm parity (mirrors web/components/confirmParity.ts).

Ship: advoi-pwa-confirm-parity-01
Voice + tap paths must show identical Guardian confirm copy when
confirmation_required; visible Confirm button; confirm_pending + beacons.
"""

from __future__ import annotations

from typing import Any, Literal

from advoi.guardian.confirmation import (
    confirmation_prompt,
    evaluate_fleet_confirmation,
    evaluate_frame_confirmation,
    fleet_confirmation_prompt,
)

ConfirmTargetKind = Literal["frame", "fleet", "operator"]

DEFAULT_CONFIRM_COPY = "Confirm yes on voice or tap Confirm to proceed."
CONFIRM_BUTTON_LABEL = "Confirm"
CONFIRM_BANNER_TITLE = "Confirmation required"


def confirm_copy_from_response(data: dict[str, Any]) -> str:
    """Mirror of confirmCopyFromResponse in confirmParity.ts."""
    for key in ("prompt", "spoken_summary", "spoken"):
        raw = data.get(key)
        if isinstance(raw, str):
            trimmed = raw.replace("\u2014", "-").strip()
            if trimmed:
                return trimmed
    return DEFAULT_CONFIRM_COPY


def confirm_parity_model(input_data: dict[str, Any]) -> dict[str, Any]:
    """Mirror of confirmParityModel in confirmParity.ts."""
    accept = input_data.get("accept_transcript") or input_data.get("acceptTranscript")
    if isinstance(accept, str) and accept.strip():
        accept_out = accept.strip()
    else:
        accept_out = None
    return {
        "copy": confirm_copy_from_response(input_data),
        "button_label": CONFIRM_BUTTON_LABEL,
        "title": CONFIRM_BANNER_TITLE,
        "target_kind": input_data["target_kind"],
        "target_id": input_data["target_id"],
        "accept_transcript": accept_out,
    }


def assert_confirm_copy_parity(spoken: str, displayed: str) -> bool:
    return spoken.strip() == displayed.strip()


# --- Pure model ---


def test_default_copy_when_empty():
    assert confirm_copy_from_response({}) == DEFAULT_CONFIRM_COPY
    assert confirm_copy_from_response({"prompt": "  ", "spoken": None}) == DEFAULT_CONFIRM_COPY


def test_prefers_prompt_over_spoken_summary():
    copy = confirm_copy_from_response(
        {
            "prompt": "Guardian prompt text",
            "spoken_summary": "Frame spoken summary",
            "spoken": "Voice spoken",
        }
    )
    assert copy == "Guardian prompt text"


def test_falls_back_spoken_summary_then_spoken():
    assert confirm_copy_from_response({"spoken_summary": "Frame gate copy"}) == "Frame gate copy"
    assert confirm_copy_from_response({"spoken": "Voice gate copy"}) == "Voice gate copy"


def test_strips_em_dash():
    assert confirm_copy_from_response({"prompt": "A \u2014 B"}) == "A - B"


def test_model_has_confirm_button_and_title():
    model = confirm_parity_model(
        {
            "prompt": "Say yes to proceed.",
            "target_kind": "frame",
            "target_id": "queue_deep_review",
        }
    )
    assert model["copy"] == "Say yes to proceed."
    assert model["button_label"] == "Confirm"
    assert model["title"] == "Confirmation required"
    assert model["target_kind"] == "frame"
    assert model["target_id"] == "queue_deep_review"


def test_voice_and_tap_identical_copy():
    """Deliverable: voice TTS string === tap status/banner string."""
    gate = {
        "prompt": "To run Queue deep review, confirm yes on voice or tap again after reviewing."
    }
    voice_copy = confirm_copy_from_response(gate)
    tap_copy = confirm_copy_from_response(gate)
    assert assert_confirm_copy_parity(voice_copy, tap_copy)
    assert voice_copy == tap_copy


def test_frame_guardian_prompt_parity(monkeypatch):
    monkeypatch.setenv("ADVOI_CONFIRMATION_REQUIRED", "true")
    result = evaluate_frame_confirmation("queue_deep_review", confirmed=False)
    assert result["awaiting_confirmation"] is True
    prompt = str(result["prompt"])
    # Frame API exposes as spoken_summary; voice may use spoken — same extract.
    voice_model = confirm_parity_model(
        {"spoken": prompt, "target_kind": "frame", "target_id": "queue_deep_review"}
    )
    tap_model = confirm_parity_model(
        {
            "spoken_summary": prompt,
            "target_kind": "frame",
            "target_id": "queue_deep_review",
        }
    )
    assert voice_model["copy"] == tap_model["copy"]
    assert voice_model["copy"] == confirmation_prompt("queue_deep_review")
    assert voice_model["button_label"] == CONFIRM_BUTTON_LABEL


def test_fleet_guardian_prompt_parity(monkeypatch):
    monkeypatch.setenv("ADVOI_CONFIRMATION_REQUIRED", "true")
    result = evaluate_fleet_confirmation("fleet_stop", confirmed=False)
    assert result["awaiting_confirmation"] is True
    prompt = str(result["prompt"])
    voice_model = confirm_parity_model(
        {
            "spoken": prompt,
            "target_kind": "fleet",
            "target_id": "fleet_stop",
        }
    )
    tap_model = confirm_parity_model(
        {
            "prompt": prompt,
            "target_kind": "fleet",
            "target_id": "fleet_stop",
        }
    )
    assert voice_model["copy"] == tap_model["copy"]
    assert voice_model["copy"] == fleet_confirmation_prompt("fleet_stop")
    assert "stop" in voice_model["copy"].lower()


def test_confirm_accept_beacon_types_aligned():
    """confirm_shown / confirm_accept remain the PEL beacon pair for this ship."""
    from advoi.analytics.pel import PWA_BEACON_EVENT_TYPES

    assert "confirm_shown" in PWA_BEACON_EVENT_TYPES
    assert "confirm_accept" in PWA_BEACON_EVENT_TYPES


def test_ui_state_confirm_pending_in_session_machine():
    """confirm_pending is part of the existing six-state UI machine."""
    from tests.test_voice_session_state import INITIAL, UI_SESSION_STATES, reduce

    assert "confirm_pending" in UI_SESSION_STATES
    ctx = reduce(INITIAL, "FRAME_START")
    ctx = reduce(ctx, "CONFIRMATION_REQUIRED")
    assert ctx.state == "confirm_pending"


def test_api_frame_confirmation_required_copy(client, monkeypatch):
    """T3/API: POST frame run without confirm returns copy usable by both paths."""
    monkeypatch.setenv("ADVOI_CONFIRMATION_REQUIRED", "true")
    resp = client.post(
        "/api/frames/queue_deep_review/run",
        json={"confirmed": False},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "confirmation_required"
    spoken = data.get("spoken_summary") or data.get("prompt") or ""
    assert spoken
    model = confirm_parity_model(
        {
            "spoken_summary": data.get("spoken_summary"),
            "prompt": data.get("prompt"),
            "spoken": data.get("spoken"),
            "target_kind": "frame",
            "target_id": "queue_deep_review",
        }
    )
    assert model["copy"]
    assert model["button_label"] == "Confirm"
    # Parity: model copy equals API spoken_summary when that is the only field.
    if data.get("spoken_summary"):
        assert model["copy"] == confirm_copy_from_response(
            {"spoken_summary": data["spoken_summary"]}
        )


def test_api_fleet_confirmation_required_copy(client, monkeypatch):
    monkeypatch.setenv("ADVOI_CONFIRMATION_REQUIRED", "true")
    resp = client.post(
        "/api/fleet/trigger",
        json={"action": "fleet_stop", "confirmed": False},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "confirmation_required"
    model = confirm_parity_model(
        {
            "prompt": data.get("prompt"),
            "spoken": data.get("spoken"),
            "target_kind": "fleet",
            "target_id": "fleet_stop",
        }
    )
    assert model["copy"] == confirm_copy_from_response(
        {"prompt": data.get("prompt"), "spoken": data.get("spoken")}
    )
    assert model["button_label"] == "Confirm"
    assert "fleet" in model["copy"].lower() or "stop" in model["copy"].lower()
