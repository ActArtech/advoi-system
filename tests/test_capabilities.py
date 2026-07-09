"""Operator capabilities and meta voice intents."""

import pytest

from advoi.voice.capabilities import (
    build_capabilities_payload,
    classify_operator_intent,
    spoken_capabilities_summary,
    spoken_firstmate_access,
    spoken_github_access,
)
from advoi.voice.respond import warm_spoken_reply


def test_build_capabilities_has_six_frames():
    payload = build_capabilities_payload()
    assert payload["frame_count"] == 6
    assert payload["specialist_count"] == 6
    assert len(payload["voice_commands"]) == 6
    assert payload["operators"]


@pytest.mark.parametrize(
    "transcript,expected",
    [
        ("what can you do", "capabilities"),
        ("list commands", "capabilities"),
        ("do you have access to github", "github_info"),
        ("run all agents", "run_all"),
        ("do you use firstmate", "firstmate_info"),
        ("fleet status", None),
    ],
)
def test_classify_operator_intent(transcript, expected):
    assert classify_operator_intent(transcript) == expected


def test_spoken_capabilities_mentions_specialists():
    text = spoken_capabilities_summary()
    assert "fleet status" in text.lower()
    assert "systems pulse" in text.lower()
    assert "specialist" in text.lower() or "agents" in text.lower()


def test_spoken_github_mentions_advoi_repo():
    text = spoken_github_access()
    assert "advoi-system" in text.lower() or "actartech" in text.lower()


@pytest.mark.asyncio
async def test_warm_spoken_reply_capabilities_no_llm():
    reply = await warm_spoken_reply("what can you do")
    assert reply.action == "capabilities"
    assert "fleet status" in reply.spoken.lower()
    assert reply.agent_id == "advoi-core"


@pytest.mark.asyncio
async def test_warm_spoken_reply_firstmate_info():
    reply = await warm_spoken_reply("do you use firstmate")
    assert reply.action == "firstmate_info"
    assert "firstmate" in reply.spoken.lower()


@pytest.mark.asyncio
async def test_warm_spoken_reply_github_info():
    reply = await warm_spoken_reply("do you have access to github")
    assert reply.action == "github_info"
    assert "github" in reply.spoken.lower()


@pytest.mark.asyncio
async def test_warm_spoken_reply_run_all_agents():
    reply = await warm_spoken_reply("run all agents")
    assert reply.action == "run_all"
    assert len(reply.agents_used or []) >= 6
    assert "systems" in reply.spoken.lower()


def test_capabilities_api(client):
    resp = client.get("/api/capabilities")
    assert resp.status_code == 200
    data = resp.json()
    assert data["frame_count"] == 6
    assert data["systems_access"]["github"]["advoi_repo"]


def test_voice_intent_capabilities(client):
    resp = client.post("/api/voice/intent", json={"transcript": "what can you do"})
    assert resp.status_code == 200
    assert resp.json()["action"] == "capabilities"