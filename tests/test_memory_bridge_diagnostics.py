"""Voice diagnostics — memory bridge health fields."""

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("ADVOI_FRAME_MOCK", "true")
os.environ.setdefault("LIVEKIT_URL", "wss://example.livekit.cloud")
os.environ.setdefault("LIVEKIT_API_KEY", "testkey")
os.environ.setdefault("LIVEKIT_API_SECRET", "testsecret")
os.environ.setdefault("OPENAI_API_KEY", "sk-test-key-for-unit-tests-only")

from advoi.api.app import _probe_memory_bridge, app  # noqa: E402


@pytest.fixture
def client():
    return TestClient(app)


@pytest.mark.asyncio
async def test_probe_memory_bridge_mock_when_url_unset(monkeypatch):
    monkeypatch.delenv("HINDSIGHT_BRIDGE_URL", raising=False)
    result = await _probe_memory_bridge()
    assert result == {"memory_bridge_ok": False, "memory_bridge_mode": "mock"}


@pytest.mark.asyncio
async def test_probe_memory_bridge_hermes_when_health_ok(monkeypatch):
    monkeypatch.setenv("HINDSIGHT_BRIDGE_URL", "http://advoi-memory-bridge:8095")

    class FakeResponse:
        def raise_for_status(self):
            return None

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url):
            assert url == "http://advoi-memory-bridge:8095/health"
            return FakeResponse()

    import httpx

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: FakeClient())

    result = await _probe_memory_bridge()
    assert result == {"memory_bridge_ok": True, "memory_bridge_mode": "hermes"}


@pytest.mark.asyncio
async def test_probe_memory_bridge_unavailable_on_probe_failure(monkeypatch):
    monkeypatch.setenv("HINDSIGHT_BRIDGE_URL", "http://advoi-memory-bridge:8095")

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url):
            raise ConnectionError("bridge unreachable")

    import httpx

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: FakeClient())

    result = await _probe_memory_bridge()
    assert result == {"memory_bridge_ok": False, "memory_bridge_mode": "unavailable"}


def test_voice_diagnostics_surfaces_hermes_bridge(client, monkeypatch):
    async def fake_probe():
        return {"memory_bridge_ok": True, "memory_bridge_mode": "hermes"}

    monkeypatch.setattr("advoi.api.app._probe_memory_bridge", fake_probe)
    data = client.get("/api/diagnostics/voice").json()
    assert data["checks"]["memory_bridge_ok"] is True
    assert data["checks"]["memory_bridge_mode"] == "hermes"
    assert not any("Memory bridge down" in w for w in data["warnings"])


def test_voice_diagnostics_warns_when_bridge_unavailable(client, monkeypatch):
    async def fake_probe():
        return {"memory_bridge_ok": False, "memory_bridge_mode": "unavailable"}

    monkeypatch.setattr("advoi.api.app._probe_memory_bridge", fake_probe)
    data = client.get("/api/diagnostics/voice").json()
    assert data["checks"]["memory_bridge_ok"] is False
    assert data["checks"]["memory_bridge_mode"] == "unavailable"
    assert any("Memory bridge down" in w for w in data["warnings"])