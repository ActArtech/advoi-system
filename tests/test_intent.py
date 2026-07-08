"""Keyword intent routing tests."""

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("ADVOI_FRAME_MOCK", "true")
os.environ.setdefault("LIVEKIT_URL", "wss://example.livekit.cloud")
os.environ.setdefault("LIVEKIT_API_KEY", "testkey")
os.environ.setdefault("LIVEKIT_API_SECRET", "testsecret")
os.environ.setdefault("OPENAI_API_KEY", "sk-test-key-for-unit-tests-only")

from advoi.api.app import app  # noqa: E402
from advoi.routing.intent import (  # noqa: E402
    classify_transcript,
    is_confirm_phrase,
    resolve_voice_action,
)
from advoi.voice.intent_processor import (  # noqa: E402
    clear_pending_frame,
    get_pending_frame,
    maybe_handle_frame_intent,
)
from advoi.voice.respond import warm_spoken_reply  # noqa: E402


@pytest.fixture
def client():
    return TestClient(app)


@pytest.mark.parametrize(
    "transcript,expected",
    [
        ("Give me a quick fleet status update", "fleet_status"),
        ("fleet status please", "fleet_status"),
        ("How is the fleet doing?", "fleet_status"),
        ("fleet scout report", "fleet_status"),
        ("What decision briefs are open right now?", "open_briefs"),
        ("open briefs", "open_briefs"),
        ("any open brief?", "open_briefs"),
        ("show me the briefs", "open_briefs"),
        ("Queue a deep review for the top priority item", "queue_deep_review"),
        ("queue deep review", "queue_deep_review"),
        ("add this to the review queue", "queue_deep_review"),
        ("please queue it", "queue_deep_review"),
        ("", None),
        ("How are you today?", None),
        ("Tell me a joke", None),
        ("We talked briefly about plans", None),
        ("code review tomorrow", None),
        ("project status update", None),
        ("scout the area", None),
        ("please queue it", "queue_deep_review"),
    ],
)
def test_classify_transcript(transcript, expected):
    assert classify_transcript(transcript) == expected


def test_resolve_voice_action_chat():
    action = resolve_voice_action("Hello there")
    assert action == {"action": "chat"}


def test_resolve_voice_action_fleet_auto_confirmed():
    action = resolve_voice_action("fleet status")
    assert action == {"action": "frame", "frame_id": "fleet_status", "confirmed": True}


def test_resolve_voice_action_review_needs_confirmation():
    action = resolve_voice_action("queue deep review")
    assert action == {
        "action": "frame",
        "frame_id": "queue_deep_review",
        "confirmed": False,
    }


def test_resolve_voice_action_review_with_confirm():
    action = resolve_voice_action("yes, queue deep review")
    assert action == {
        "action": "frame",
        "frame_id": "queue_deep_review",
        "confirmed": True,
    }


@pytest.mark.parametrize(
    "transcript,expected",
    [
        ("yes", True),
        ("Yeah go ahead", True),
        ("ok", True),
        ("fleet status", False),
        ("no", False),
        ("", False),
    ],
)
def test_is_confirm_phrase(transcript, expected):
    assert is_confirm_phrase(transcript) is expected


@pytest.mark.asyncio
async def test_warm_spoken_reply_routes_fleet_frame():
    spoken = await warm_spoken_reply("Give me a fleet status update")
    assert "fleet" in spoken.lower()


@pytest.mark.asyncio
async def test_warm_spoken_reply_routes_briefs_frame():
    spoken = await warm_spoken_reply("What open briefs do we have?")
    assert "brief" in spoken.lower()


@pytest.mark.asyncio
async def test_warm_spoken_reply_review_asks_confirmation():
    spoken = await warm_spoken_reply("queue deep review")
    assert "confirm" in spoken.lower() or "confirmation" in spoken.lower()


@pytest.mark.asyncio
async def test_warm_spoken_reply_still_uses_llm_for_chat(monkeypatch):
    class FakeResp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "Sure, here is a quick take."}}]}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return None

        async def post(self, *a, **k):
            return FakeResp()

    import httpx

    monkeypatch.setattr(httpx, "AsyncClient", lambda **k: FakeClient())
    spoken = await warm_spoken_reply("What is open?", recent_phrases=["open"])
    assert "quick take" in spoken.lower()


def test_voice_intent_endpoint_classifies_frame(client):
    resp = client.post(
        "/api/voice/intent",
        json={"transcript": "fleet status update"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == "frame"
    assert data["frame_id"] == "fleet_status"
    assert data["confirmed"] is True
    assert data["preview"] is None


def test_voice_intent_endpoint_chat(client):
    resp = client.post(
        "/api/voice/intent",
        json={"transcript": "How are you doing?"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == "chat"
    assert data["frame_id"] is None


@pytest.mark.asyncio
async def test_maybe_handle_frame_intent_routes_fleet():
    spoken: list[str] = []

    async def speak(text: str) -> None:
        spoken.append(text)

    handled = await maybe_handle_frame_intent(
        "fleet status update",
        session_id="voice-test",
        speak=speak,
    )
    assert handled is True
    assert spoken
    assert "fleet" in spoken[0].lower()


@pytest.mark.asyncio
async def test_maybe_handle_frame_intent_passes_chat():
    spoken: list[str] = []

    async def speak(text: str) -> None:
        spoken.append(text)

    handled = await maybe_handle_frame_intent(
        "How are you today?",
        session_id="voice-test",
        speak=speak,
    )
    assert handled is False
    assert spoken == []


@pytest.mark.asyncio
async def test_maybe_handle_frame_intent_review_two_turn_confirmation():
    session_id = "confirm-test-session"
    clear_pending_frame(session_id)
    spoken: list[str] = []

    async def speak(text: str) -> None:
        spoken.append(text)

    handled = await maybe_handle_frame_intent(
        "queue deep review",
        session_id=session_id,
        speak=speak,
    )
    assert handled is True
    assert spoken
    assert "confirm" in spoken[0].lower() or "confirmation" in spoken[0].lower()
    assert get_pending_frame(session_id) == "queue_deep_review"

    spoken.clear()
    handled = await maybe_handle_frame_intent(
        "yes",
        session_id=session_id,
        speak=speak,
    )
    assert handled is True
    assert spoken
    assert get_pending_frame(session_id) is None
    assert "queued deep review" in spoken[0].lower()
    assert "confirm yes on voice" not in spoken[0].lower()


@pytest.mark.asyncio
async def test_maybe_handle_frame_intent_bare_yes_without_pending_is_chat():
    session_id = "no-pending-session"
    clear_pending_frame(session_id)
    spoken: list[str] = []

    async def speak(text: str) -> None:
        spoken.append(text)

    handled = await maybe_handle_frame_intent(
        "yes",
        session_id=session_id,
        speak=speak,
    )
    assert handled is False
    assert spoken == []
    assert get_pending_frame(session_id) is None


def test_voice_intent_endpoint_preview(client):
    resp = client.post(
        "/api/voice/intent",
        json={"transcript": "open briefs", "preview": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["frame_id"] == "open_briefs"
    assert data["preview"]["agent_id"] == "brief-curator"
    assert data["preview"]["spoken_summary"]