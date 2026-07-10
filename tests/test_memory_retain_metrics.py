"""T0: retain failure WARNING + counter on /api/diagnostics/platform (ADR-026).

Task: advoi-memory-retain-metrics-01
Simulated Hindsight/Letta retain failures must log WARNING, increment the
in-process counter, and appear in platform diagnostics JSON.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from advoi.memory.hindsight import retain_strategic
from advoi.memory.letta_client import LettaConfig, retain_passage
from advoi.memory.retain_metrics import (
    reset_retain_failure_metrics,
    retain_failure_count,
    retain_metrics_snapshot,
)


@pytest.fixture(autouse=True)
def _reset_metrics():
    reset_retain_failure_metrics()
    yield
    reset_retain_failure_metrics()


@pytest.mark.asyncio
async def test_hindsight_retain_bridge_failure_increments_metric(caplog):
    import logging

    with (
        patch("advoi.memory.hindsight._bridge_call", new_callable=AsyncMock) as bridge,
        patch("advoi.memory.hindsight._retain_direct", new_callable=AsyncMock) as direct,
        patch.dict(
            "os.environ",
            {"HINDSIGHT_BRIDGE_URL": "http://bridge.test", "HINDSIGHT_MODE": "local"},
            clear=False,
        ),
        caplog.at_level(logging.WARNING, logger="advoi.memory.retain_metrics"),
    ):
        # Force bridge path via env; bridge returns not-ok.
        from advoi.memory import hindsight as hs

        hs._hindsight_settings.cache_clear()
        bridge.return_value = {"ok": False, "error": "upstream timeout"}

        ok = await retain_strategic(
            "portfolio_fact",
            {"summary": "Clapart stage explore"},
        )

    assert ok is False
    assert retain_failure_count() == 1
    snap = retain_metrics_snapshot()
    assert snap["last_retain_failure"]["backend"] == "hindsight"
    assert snap["last_retain_failure"]["event_type"] == "portfolio_fact"
    assert "upstream timeout" in (snap["last_retain_failure"].get("detail") or "")
    direct.assert_not_called()
    assert any("memory retain failed" in r.message for r in caplog.records)
    # No secret-shaped payload dump
    joined = " ".join(r.message for r in caplog.records)
    assert "api_key" not in joined.lower()


@pytest.mark.asyncio
async def test_hindsight_retain_exception_increments_metric(caplog):
    import logging

    with (
        patch(
            "advoi.memory.hindsight._bridge_call",
            new_callable=AsyncMock,
            side_effect=RuntimeError("connection refused"),
        ),
        patch.dict(
            "os.environ",
            {"HINDSIGHT_BRIDGE_URL": "http://bridge.test"},
            clear=False,
        ),
        caplog.at_level(logging.WARNING, logger="advoi.memory.retain_metrics"),
    ):
        from advoi.memory import hindsight as hs

        hs._hindsight_settings.cache_clear()
        ok = await retain_strategic("portfolio_fact", {"summary": "clean fact"})

    assert ok is False
    assert retain_failure_count() == 1
    assert retain_metrics_snapshot()["last_retain_failure"]["reason"] == "RuntimeError"
    assert any("RuntimeError" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_letta_retain_http_error_increments_metric(caplog):
    import logging

    cfg = LettaConfig(
        enabled=True,
        base_url="http://letta.test",
        agent_id="advoi-executive",
        api_key="",
    )

    class FakeResponse:
        status_code = 503
        text = "service unavailable"

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, *args, **kwargs):
            return FakeResponse()

    with (
        patch("httpx.AsyncClient", return_value=FakeClient()),
        caplog.at_level(logging.WARNING, logger="advoi.memory.retain_metrics"),
    ):
        ok = await retain_passage(
            "squad_lesson",
            {"summary": "scout tick ok"},
            cfg=cfg,
        )

    assert ok is False
    assert retain_failure_count() == 1
    last = retain_metrics_snapshot()["last_retain_failure"]
    assert last["backend"] == "letta"
    assert last["reason"] == "http_503"
    assert any("letta" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_letta_disabled_does_not_count_as_failure():
    cfg = LettaConfig(enabled=False, base_url="http://letta.test", agent_id="x", api_key="")
    ok = await retain_passage("squad_lesson", {"summary": "x"}, cfg=cfg)
    assert ok is False
    assert retain_failure_count() == 0


@pytest.mark.asyncio
async def test_fleet_backlog_reject_does_not_increment_retain_failure():
    """Policy reject already WARNs; it is not a backend retain-failure metric."""
    ok = await retain_strategic(
        "portfolio_fact",
        {"summary": "# backlog\n\n## Queued\n- item"},
    )
    assert ok is False
    assert retain_failure_count() == 0


def test_simulated_retain_failure_appears_in_platform_diagnostics(client):
    """T0 acceptance: counter surfaces on GET /api/diagnostics/platform."""
    from advoi.memory.retain_metrics import record_retain_failure

    before = client.get("/api/diagnostics/platform").json()
    assert "retain_failure_count" in before
    assert before["retain_failure_count"] == 0
    assert before["memory"]["retain_failure_count"] == 0

    record_retain_failure(
        backend="hindsight",
        event_type="portfolio_fact",
        reason="simulated",
        detail="t0",
    )

    data = client.get("/api/diagnostics/platform").json()
    assert data["retain_failure_count"] == 1
    assert data["memory"]["retain_failure_count"] == 1
    assert data["memory"]["last_retain_failure"]["backend"] == "hindsight"
    assert data["memory"]["last_retain_failure"]["event_type"] == "portfolio_fact"
    assert data["memory"]["last_retain_failure"]["reason"] == "simulated"
