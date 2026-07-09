"""Guardian two-phase notification tests."""

from __future__ import annotations

import pytest

from advoi.guardian.notifications import notify_issue_detected, notify_issue_resolved


@pytest.mark.asyncio
async def test_detected_then_resolved(tmp_path, monkeypatch):
    log_path = tmp_path / "guardian.jsonl"
    monkeypatch.setenv("GUARDIAN_LOG_PATH", str(log_path))

    issue_id = await notify_issue_detected(
        "fleet-scout",
        error="tick failed",
        recovery_hint="retry",
    )
    assert issue_id

    resolved = await notify_issue_resolved("fleet-scout", note="recovered")
    assert resolved is True

    text = log_path.read_text(encoding="utf-8")
    assert "issue_detected" in text
    assert "issue_resolved" in text