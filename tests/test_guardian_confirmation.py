"""Guardian confirmation harness tests."""

from __future__ import annotations

from advoi.guardian.confirmation import (
    evaluate_frame_confirmation,
    frame_needs_confirmation,
    global_confirmation_enabled,
)


def test_review_frame_needs_confirmation(monkeypatch):
    monkeypatch.setenv("ADVOI_CONFIRMATION_REQUIRED", "true")
    assert frame_needs_confirmation("queue_deep_review") is True
    assert frame_needs_confirmation("fleet_status") is False


def test_confirmation_disabled(monkeypatch):
    monkeypatch.setenv("ADVOI_CONFIRMATION_REQUIRED", "false")
    assert global_confirmation_enabled() is False
    assert frame_needs_confirmation("queue_deep_review") is False


def test_evaluate_blocks_without_confirm(monkeypatch):
    monkeypatch.setenv("ADVOI_CONFIRMATION_REQUIRED", "true")
    result = evaluate_frame_confirmation("queue_deep_review", confirmed=False)
    assert result["proceed"] is False
    assert result["awaiting_confirmation"] is True
    assert "prompt" in result


def test_evaluate_accepts_yes_phrase(monkeypatch):
    monkeypatch.setenv("ADVOI_CONFIRMATION_REQUIRED", "true")
    result = evaluate_frame_confirmation(
        "queue_deep_review",
        confirmed=False,
        transcript="yes go ahead",
    )
    assert result["proceed"] is True