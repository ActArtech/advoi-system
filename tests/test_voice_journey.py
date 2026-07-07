"""Voice PWA journey matrix — API paths for staging smoke gates."""

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("ADVOI_FRAME_MOCK", "true")
os.environ.setdefault("LIVEKIT_URL", "wss://example.livekit.cloud")
os.environ.setdefault("LIVEKIT_API_KEY", "testkey")
os.environ.setdefault("LIVEKIT_API_SECRET", "testsecret")
os.environ.setdefault("OPENAI_API_KEY", "sk-test-key-for-unit-tests-only")

from advoi.api.app import app  # noqa: E402


@pytest.fixture
def client():
    return TestClient(app)


def test_journey_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["stage"] == "voice-pwa-2"


def test_journey_token(client):
    resp = client.post("/api/livekit/token", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["token"]
    assert data["room_name"] == "advoi-voice"


def test_journey_session_lists_frames_and_agents(client):
    resp = client.get("/api/session")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["frames"]) == 3
    assert len(data["agents"]) == 3


def test_journey_diagnostics(client):
    resp = client.get("/api/diagnostics/voice")
    assert resp.status_code == 200
    data = resp.json()
    assert data["checks"]["frames"] == 3
    assert data["checks"]["llm_key"] is True


@pytest.mark.parametrize(
    "frame_id,agent_id",
    [
        ("fleet_status", "fleet-scout"),
        ("open_briefs", "brief-curator"),
        ("queue_deep_review", "review-queue"),
    ],
)
def test_journey_frame_run_mock(client, frame_id, agent_id):
    body = {"confirmed": frame_id == "queue_deep_review"}
    resp = client.post(f"/api/frames/{frame_id}/run", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["agent_id"] == agent_id
    assert data["spoken_summary"]