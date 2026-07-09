import os

import pytest

os.environ.setdefault("OPENAI_API_KEY", "sk-test")
os.environ.setdefault("ADVOI_FRAME_MOCK", "true")

from advoi.voice.respond import warm_spoken_reply  # noqa: E402


@pytest.mark.asyncio
async def test_empty_transcript():
    reply = await warm_spoken_reply("")
    assert "did not catch" in reply.spoken.lower()


@pytest.mark.asyncio
async def test_mocked_llm(monkeypatch):
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
    reply = await warm_spoken_reply("What is open?", recent_phrases=["open"])
    assert "quick take" in reply.spoken.lower()
    assert reply.action == "chat"