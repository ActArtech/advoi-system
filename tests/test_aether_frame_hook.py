"""Aether post-frame memory hook tests."""

import os

import pytest

os.environ.setdefault("ADVOI_FRAME_MOCK", "true")
os.environ.setdefault("OPENAI_API_KEY", "sk-test")
os.environ.setdefault("LIVEKIT_URL", "wss://example.livekit.cloud")
os.environ.setdefault("LIVEKIT_API_KEY", "testkey")
os.environ.setdefault("LIVEKIT_API_SECRET", "testsecret")

from advoi.routing.frame_runner import run_frame  # noqa: E402


@pytest.mark.asyncio
async def test_run_frame_enriches_aether_detail(tmp_path, monkeypatch):
    monkeypatch.setenv("ADVOI_OPERATIONAL_STORE", str(tmp_path / "ops.jsonl"))
    monkeypatch.setenv("ADVOI_OPERATIONAL_STORE_ENABLED", "true")
    monkeypatch.setenv("LETTA_ENABLED", "false")

    result = await run_frame("fleet_status", refresh=True)
    assert result.detail.get("aether_routed") is True
    assert "venture_id" in result.detail