"""Shared pytest config — fast, isolated test env (no Docker Redis DNS hangs)."""

from __future__ import annotations

import os

# Set before any advoi.api.app import (avoids blocking on host "redis" DNS).
os.environ.setdefault("ADVOI_FRAME_MOCK", "true")
os.environ.setdefault("ADVOI_PREWARM_AGENTS", "false")
os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6399/0")
os.environ.setdefault("LIVEKIT_URL", "wss://example.livekit.cloud")
os.environ.setdefault("LIVEKIT_API_KEY", "testkey")
os.environ.setdefault("LIVEKIT_API_SECRET", "testsecret")
os.environ.setdefault("OPENAI_API_KEY", "sk-test-key-for-unit-tests-only")

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from advoi.api.app import app

    with TestClient(app) as test_client:
        yield test_client