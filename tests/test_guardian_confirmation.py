"""Guardian confirmation harness tests."""

from __future__ import annotations

from advoi.guardian.confirmation import (
    evaluate_fleet_confirmation,
    evaluate_frame_confirmation,
    fleet_action_needs_confirmation,
    frame_needs_confirmation,
    global_confirmation_enabled,
    high_risk_fleet_actions,
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


def test_start_development_needs_guardian_confirm(monkeypatch):
    monkeypatch.setenv("ADVOI_CONFIRMATION_REQUIRED", "true")
    assert fleet_action_needs_confirmation("start_development") is True
    assert "start_development" in high_risk_fleet_actions()


def test_fleet_confirm_blocks_without_approval(monkeypatch):
    monkeypatch.setenv("ADVOI_CONFIRMATION_REQUIRED", "true")
    result = evaluate_fleet_confirmation("start_development", confirmed=False)
    assert result["proceed"] is False
    assert result["awaiting_confirmation"] is True
    assert "start development" in str(result.get("prompt", "")).lower()


def test_fleet_confirm_accepts_confirm_phrase(monkeypatch):
    monkeypatch.setenv("ADVOI_CONFIRMATION_REQUIRED", "true")
    result = evaluate_fleet_confirmation(
        "start_development",
        confirmed=False,
        transcript="start development on clapart confirm",
    )
    assert result["proceed"] is True


def test_fleet_confirm_accepts_go(monkeypatch):
    monkeypatch.setenv("ADVOI_CONFIRMATION_REQUIRED", "true")
    result = evaluate_fleet_confirmation(
        "wake_firstmate",
        confirmed=False,
        transcript="go",
    )
    assert result["proceed"] is True
    soft = evaluate_fleet_confirmation("wake_firstmate", confirmed=False)
    assert soft["proceed"] is False
    assert "go" in str(soft.get("prompt", "")).lower()


def test_fleet_confirm_disabled_when_global_off(monkeypatch):
    monkeypatch.setenv("ADVOI_CONFIRMATION_REQUIRED", "false")
    assert fleet_action_needs_confirmation("start_development") is False
    result = evaluate_fleet_confirmation("start_development", confirmed=False)
    assert result["proceed"] is True