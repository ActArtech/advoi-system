"""Server-side TTS endpoint tests."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_synthesize_speech_requires_text():
    from advoi.voice.server_tts import synthesize_speech

    with pytest.raises(ValueError, match="text is required"):
        await synthesize_speech("   ")


def test_voice_speak_returns_mp3(client, monkeypatch):
    async def fake_synthesize(text, *, voice=None):
        assert text == "Hello ADVoi"
        return b"\xff\xfb\x90\x00fake-mp3"

    monkeypatch.setattr("advoi.api.app.synthesize_speech", fake_synthesize)

    resp = client.post(
        "/api/voice/speak",
        json={"text": "Hello ADVoi", "voice": "alloy"},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "audio/mpeg"
    assert resp.content.startswith(b"\xff\xfb")


def test_voice_speak_rejects_empty_text(client):
    resp = client.post("/api/voice/speak", json={"text": "  "})
    assert resp.status_code == 400