"""Decision frame and multi-agent routing tests."""

import os

import pytest

os.environ.setdefault("ADVOI_FRAME_MOCK", "true")
os.environ.setdefault("LIVEKIT_URL", "wss://example.livekit.cloud")
os.environ.setdefault("LIVEKIT_API_KEY", "testkey")
os.environ.setdefault("LIVEKIT_API_SECRET", "testsecret")
os.environ.setdefault("OPENAI_API_KEY", "sk-test-key-for-unit-tests-only")

from advoi.decision.frames import FRAMES, get_frame  # noqa: E402
from advoi.routing.frame_runner import run_frame  # noqa: E402
from advoi.voice.frame_dispatch import handle_frame_message  # noqa: E402


@pytest.mark.asyncio
async def test_frame_catalog_has_three_agents():
    assert len(FRAMES) == 3
    assert get_frame("fleet_status")
    assert get_frame("open_briefs")
    assert get_frame("queue_deep_review")


@pytest.mark.asyncio
async def test_run_fleet_frame_mock():
    result = await run_frame("fleet_status")
    assert result.agent_id == "fleet-scout"
    assert result.status == "ok"
    assert "Fleet mock" in result.spoken_summary


@pytest.mark.asyncio
async def test_run_briefs_frame_mock():
    result = await run_frame("open_briefs")
    assert result.agent_id == "brief-curator"
    assert "brief" in result.spoken_summary.lower()


@pytest.mark.asyncio
async def test_review_requires_confirmation():
    result = await run_frame("queue_deep_review", confirmed=False)
    assert result.status == "confirmation_required"
    assert result.detail.get("awaiting_confirmation") is True

    confirmed = await run_frame("queue_deep_review", confirmed=True)
    assert confirmed.status == "ok"
    assert confirmed.detail.get("queued") is True


@pytest.mark.asyncio
async def test_data_channel_speak_payload():
    spoken = await handle_frame_message(b'{"type":"speak","text":"Hello from test."}')
    assert spoken == "Hello from test."


@pytest.mark.asyncio
async def test_data_channel_frame_payload():
    spoken = await handle_frame_message(b'{"type":"frame","frame_id":"fleet_status"}')
    assert spoken
    assert "fleet" in spoken.lower() or "Fleet" in spoken