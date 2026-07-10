"""T0: ADR-026 never-rule — fleet backlog text must not reach Hindsight retain.

Task: advoi-memory-fleet-recall-guard-01
Proves retain / write_targets paths reject backlog-shaped payloads before any
Hindsight persist (mock/fixture pattern, no live bridge).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from advoi.memory.hindsight import retain_strategic
from advoi.memory.router import MemoryConfig, MemoryRouter
from advoi.memory.write_targets import (
    MemoryEventType,
    WriteTarget,
    payload_has_fleet_backlog,
    targets_for,
    text_looks_like_fleet_backlog,
)

# Sample raw fleet backlog (shape matches tests/test_fleet_snapshot.py fixture).
SAMPLE_FLEET_BACKLOG = """# backlog

## In flight
_(none)_

## Queued
- [ ] **fe-redirect-external-01** - Off-topic handoff
- [ ] **fe-relief-checkin-01** - Relief prompt
"""

CLEAN_PORTFOLIO = {
    "summary": "Clapart venture: redirect external handoff decision accepted.",
    "venture_id": "clapart",
}


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (SAMPLE_FLEET_BACKLOG, True),
        ("run_next_backlog", True),
        ("fleet backlog dump for recall", True),
        ("FIRSTMATE_FLEET_PATH=/data/fleet", True),
        ("# backlog\n\n## Queued\n- item", True),
        ("Portfolio stage: explore; optionality high.", False),
        ("Clapart: fleet_status frame ran OK.", False),
        ("", False),
    ],
)
def test_text_looks_like_fleet_backlog(text: str, expected: bool):
    assert text_looks_like_fleet_backlog(text) is expected


def test_payload_has_fleet_backlog_on_summary_and_nested():
    assert payload_has_fleet_backlog({"summary": SAMPLE_FLEET_BACKLOG}) is True
    assert payload_has_fleet_backlog({"text": SAMPLE_FLEET_BACKLOG}) is True
    assert payload_has_fleet_backlog({"detail": {"snapshot": SAMPLE_FLEET_BACKLOG}}) is True
    assert payload_has_fleet_backlog(CLEAN_PORTFOLIO) is False
    assert payload_has_fleet_backlog(None) is False


def test_strategic_events_still_target_hindsight():
    """Guard is payload-level; map still routes strategic events to Hindsight."""
    for event in (
        MemoryEventType.PORTFOLIO_FACT,
        MemoryEventType.GOVERNANCE_DECISION,
        MemoryEventType.CROSS_PROJECT_SYNTHESIS,
        MemoryEventType.VENTURE_BELIEF_UPDATE,
    ):
        assert WriteTarget.HINDSIGHT in targets_for(event)


@pytest.mark.asyncio
async def test_retain_strategic_rejects_fleet_backlog_never_persists():
    """Last-mile Hindsight path: backlog payload must not call bridge or client."""
    with (
        patch("advoi.memory.hindsight._bridge_call", new_callable=AsyncMock) as bridge,
        patch("advoi.memory.hindsight._retain_direct", new_callable=AsyncMock) as direct,
    ):
        bridge.return_value = {"ok": True}
        direct.return_value = True

        ok = await retain_strategic(
            "portfolio_fact",
            {"summary": SAMPLE_FLEET_BACKLOG, "source": "fleet-scout"},
        )

    assert ok is False
    bridge.assert_not_called()
    direct.assert_not_called()


@pytest.mark.asyncio
async def test_retain_strategic_allows_clean_portfolio_fact():
    with (
        patch("advoi.memory.hindsight._hindsight_settings") as settings,
        patch("advoi.memory.hindsight._bridge_call", new_callable=AsyncMock) as bridge,
        patch("advoi.memory.hindsight._retain_direct", new_callable=AsyncMock) as direct,
    ):
        settings.return_value = {
            "mode": "cloud",
            "bridge": "",
            "api_url": "https://api.example.test",
            "api_key": "",
            "bank_id": "advoi-portfolio",
            "hermes_container": "hermes",
        }
        direct.return_value = True

        ok = await retain_strategic("portfolio_fact", CLEAN_PORTFOLIO)

    assert ok is True
    direct.assert_awaited_once()
    bridge.assert_not_called()
    summary = direct.await_args.args[1]
    assert not text_looks_like_fleet_backlog(summary)
    assert "Clapart" in summary


@pytest.mark.asyncio
async def test_router_retain_hindsight_rejects_sample_backlog(monkeypatch: pytest.MonkeyPatch):
    """MemoryRouter path: Hindsight result False; retain_strategic never invoked."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("HINDSIGHT_BRIDGE_URL", raising=False)

    calls: list[tuple[str, dict[str, Any]]] = []

    async def _capture(event_type: str, payload: dict[str, Any], **kwargs: Any) -> bool:
        calls.append((event_type, payload))
        return True

    cfg = MemoryConfig(hindsight_enabled=True, letta_enabled=False, database_url="", redis_url="")
    router = MemoryRouter(cfg)

    # Router imports retain_strategic inside the method from advoi.memory.hindsight.
    with patch("advoi.memory.hindsight.retain_strategic", new=AsyncMock(side_effect=_capture)):
        results = await router.retain(
            MemoryEventType.PORTFOLIO_FACT,
            {"summary": SAMPLE_FLEET_BACKLOG},
        )

    assert results.get("hindsight") is False
    assert calls == []


@pytest.mark.asyncio
async def test_router_retain_clean_payload_reaches_hindsight(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)

    mock_retain = AsyncMock(return_value=True)
    cfg = MemoryConfig(hindsight_enabled=True, letta_enabled=False, database_url="", redis_url="")
    router = MemoryRouter(cfg)

    with patch("advoi.memory.hindsight.retain_strategic", mock_retain):
        results = await router.retain(MemoryEventType.PORTFOLIO_FACT, CLEAN_PORTFOLIO)

    assert results.get("hindsight") is True
    mock_retain.assert_awaited_once()
    payload = mock_retain.await_args.args[1]
    assert payload_has_fleet_backlog(payload) is False


@pytest.mark.asyncio
async def test_end_to_end_hindsight_path_never_persists_backlog_text():
    """retain_strategic with mocked direct path: only clean summary is persisted."""
    with (
        patch("advoi.memory.hindsight._hindsight_settings") as settings,
        patch("advoi.memory.hindsight._bridge_call", new_callable=AsyncMock) as bridge,
        patch(
            "advoi.memory.hindsight._retain_direct",
            new_callable=AsyncMock,
            return_value=True,
        ) as direct,
    ):
        settings.return_value = {
            "mode": "cloud",
            "bridge": "",
            "api_url": "https://api.example.test",
            "api_key": "k",
            "bank_id": "advoi-portfolio",
            "hermes_container": "hermes",
        }
        bridge.return_value = None

        rejected = await retain_strategic(
            "venture_belief_update",
            {
                "summary": SAMPLE_FLEET_BACKLOG,
                "venture": "clapart",
            },
        )
        allowed = await retain_strategic(
            "venture_belief_update",
            {
                "summary": "Clapart: fleet_status frame ran OK.",
                "venture": "clapart",
            },
        )

    assert rejected is False
    assert allowed is True
    direct.assert_awaited_once()  # only clean payload
    summary_arg = direct.await_args.args[1]
    assert "fe-redirect-external-01" not in summary_arg
    assert "# backlog" not in summary_arg
    assert "ran OK" in summary_arg
