"""Voice PWA journey matrix — API paths for staging smoke gates."""

import pytest


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
    assert len(data["frames"]) == 6
    assert len(data["agents"]) == 6


def test_journey_diagnostics(client):
    resp = client.get("/api/diagnostics/voice")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["checks"]["frames"] == 6
    assert data["checks"]["llm_key"] is True
    assert "advoi-voice" in data["voice_agent_hint"]
    assert data["reason"] is None
    assert data["latency"]["frame_run_ms"] is not None
    assert data["checks"]["frame_run_ms"] == data["latency"]["frame_run_ms"]
    assert data["checks"]["memory_bridge_mode"] == "mock"
    assert data["checks"]["memory_bridge_ok"] is False


def test_journey_latency_diagnostics(client):
    resp = client.get("/api/diagnostics/latency")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    timings = data["timings_ms"]
    assert timings["health_ms"] is not None
    assert timings["token_ms"] is not None
    assert timings["frame_run_ms"] is not None
    assert timings["intent_ms"] is not None
    assert timings["respond_ms"] is not None
    assert timings["api_voice_path_ms"] is not None
    assert data["sla_target_ms"] == 800.0
    assert data["sla_ok"] is True
    assert data["frame_id"] == "fleet_status"
    assert "sla_scope" in data


def test_journey_diagnostics_missing_llm_key(client, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    resp = client.get("/api/diagnostics/voice")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert data["checks"]["llm_key"] is False
    assert data["checks"]["llm_key_required"] is True
    assert data["warnings"]
    assert "OPENROUTER_API_KEY or OPENAI_API_KEY" in data["warnings"][0]
    assert "advoi-voice" in data["voice_agent_hint"]
    assert "OPENROUTER_API_KEY or OPENAI_API_KEY" in data["reason"]


@pytest.mark.parametrize(
    "frame_id,agent_id",
    [
        ("fleet_status", "fleet-scout"),
        ("open_briefs", "brief-curator"),
        ("queue_deep_review", "review-queue"),
        ("systems_pulse", "systems-pulse"),
        ("memory_health", "memory-scout"),
        ("guardian_status", "guardian-sentinel"),
    ],
)
def test_journey_frame_run_mock(client, frame_id, agent_id):
    body = {"confirmed": frame_id == "queue_deep_review"}
    resp = client.post(f"/api/frames/{frame_id}/run", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["agent_id"] == agent_id
    assert data["spoken_summary"]


def test_journey_frame_refresh_query_param(client):
    resp = client.post("/api/frames/fleet_status/run?refresh=true", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["agent_id"] == "fleet-scout"
    assert data["spoken_summary"]


def test_journey_voice_respond_empty(client):
    resp = client.post("/api/voice/respond", json={"transcript": ""})
    assert resp.status_code == 200
    assert "did not catch" in resp.json()["spoken"].lower()


def test_journey_voice_respond_mocked(monkeypatch, client):
    from advoi.voice.respond import VoiceReply

    async def fake_reply(transcript, **kwargs):
        assert transcript == "hello portfolio"
        assert kwargs.get("session_id") == "voice-local"
        return VoiceReply(
            spoken="Quick take on your portfolio.",
            action="chat",
            agent_id="advoi-core",
            agent_name="ADVoi Core",
        )

    monkeypatch.setattr("advoi.api.app.warm_spoken_reply", fake_reply)
    resp = client.post(
        "/api/voice/respond",
        json={"transcript": "hello portfolio", "recent_phrases": ["portfolio"]},
    )
    assert resp.status_code == 200
    assert resp.json()["spoken"] == "Quick take on your portfolio."


def test_journey_diagnostics_voice_local_mode(client, monkeypatch):
    monkeypatch.setenv("ADVOI_VOICE_MODE", "local")
    resp = client.get("/api/diagnostics/voice")
    assert resp.status_code == 200
    data = resp.json()
    assert data["voice_mode"] == "local"
    assert data["checks"]["voice_respond_ready"] is True