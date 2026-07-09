"""Parallel agent bootstrap tests."""

import os

import pytest

os.environ.setdefault("ADVOI_FRAME_MOCK", "true")
os.environ.setdefault("OPENAI_API_KEY", "sk-test")

from advoi.routing.agent_bootstrap import prewarm_all_agents, tick_agent  # noqa: E402


@pytest.mark.asyncio
async def test_tick_agent_fleet_mock():
    payload = await tick_agent("fleet-scout", refresh=True)
    assert payload
    assert payload["status"] == "ok"
    assert "fleet" in payload["spoken_summary"].lower()


@pytest.mark.asyncio
async def test_prewarm_all_parallel():
    results = await prewarm_all_agents()
    assert len(results) == 6