"""API smoke tests."""

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("LIVEKIT_URL", "wss://example.livekit.cloud")
os.environ.setdefault("LIVEKIT_API_KEY", "testkey")
os.environ.setdefault("LIVEKIT_API_SECRET", "testsecret")

from advoi.api.app import app  # noqa: E402


@pytest.fixture
def client():
    return TestClient(app)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["stage"] == "voice-pwa-2"


def test_livekit_token(client):
    resp = client.post("/api/livekit/token", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["token"]
    assert data["url"] == "wss://example.livekit.cloud"
    assert data["room_name"] == "advoi-voice"