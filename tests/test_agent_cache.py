"""Agent cache layer tests."""

import os

import pytest

os.environ.setdefault("ADVOI_FRAME_MOCK", "true")
os.environ.setdefault("OPENAI_API_KEY", "sk-test")

from advoi.cache.agent_cache import CACHEABLE_STATUSES, write_agent_cache  # noqa: E402
from advoi.routing.agent_bootstrap import tick_agent  # noqa: E402


def test_cacheable_statuses_include_confirmation():
    assert "confirmation_required" in CACHEABLE_STATUSES


@pytest.mark.asyncio
async def test_review_queue_tick_returns_confirm_status():
    payload = await tick_agent("review-queue", refresh=True)
    assert payload
    assert payload["status"] == "confirmation_required"