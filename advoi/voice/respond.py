"""Warm spoken replies for client-side voice loop."""

from __future__ import annotations

import logging

import httpx

from advoi.copy_style import plain_copy
from advoi.llm.openrouter import resolve_llm_credentials
from advoi.memory import MemoryRouter
from advoi.routing.frame_runner import run_frame
from advoi.routing.intent import resolve_voice_action
from advoi.voice.memory_hooks import retain_turn
from advoi.voice.prompts import LOCAL_VOICE_SESSION, build_warm_system_instruction

_LOGGER = logging.getLogger(__name__)


async def _memory_context(*, session_id: str, query: str) -> str:
    router = MemoryRouter()
    recall = await router.recall(session_id=session_id, query=query)
    chunks: list[str] = []
    for item in recall.strategic + recall.operational + recall.ephemeral:
        text = item.get("text") or item.get("content") or item.get("summary")
        if text:
            chunks.append(str(text))
    return "\n".join(chunks[:6])


async def warm_spoken_reply(
    transcript: str,
    *,
    recent_phrases: list[str] | None = None,
    session_id: str = LOCAL_VOICE_SESSION,
    temperature: float = 0.8,
) -> str:
    text = (transcript or "").strip()
    if not text:
        return "I did not catch that. Try again when you are ready."

    action = resolve_voice_action(text)
    if action["action"] == "frame":
        result = await run_frame(
            action["frame_id"],
            confirmed=action["confirmed"],
        )
        spoken = plain_copy(result.spoken_summary)
        try:
            await retain_turn(session_id=session_id, role="user", text=text)
            await retain_turn(session_id=session_id, role="assistant", text=spoken)
        except Exception as exc:
            _LOGGER.debug("voice-local frame retain skip: %s", exc)
        return spoken

    memory_context = ""
    try:
        memory_context = await _memory_context(session_id=session_id, query=text)
    except Exception as exc:
        _LOGGER.debug("voice-local recall skip: %s", exc)

    creds = resolve_llm_credentials()
    base_url = (creds.base_url or "https://api.openai.com/v1").rstrip("/")

    messages: list[dict[str, str]] = [
        {"role": "system", "content": build_warm_system_instruction(memory_context=memory_context)},
    ]
    if recent_phrases:
        mirror = ", ".join(p for p in recent_phrases if p.strip())[:120]
        if mirror:
            messages.append(
                {
                    "role": "system",
                    "content": f"Mirror one or two of these user phrases lightly: {mirror}",
                }
            )
    messages.append({"role": "user", "content": text})

    headers = {"Authorization": f"Bearer {creds.api_key}", "Content-Type": "application/json"}
    if creds.provider == "openrouter":
        headers["HTTP-Referer"] = "https://advoi.keyteller.com"
        headers["X-Title"] = "ADVoi local voice loop"

    async with httpx.AsyncClient(timeout=45.0) as client:
        resp = await client.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json={
                "model": creds.llm_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": 220,
            },
        )
        resp.raise_for_status()
        raw = resp.json()["choices"][0]["message"]["content"]

    spoken = plain_copy(str(raw).strip())

    try:
        await retain_turn(session_id=session_id, role="user", text=text)
        await retain_turn(session_id=session_id, role="assistant", text=spoken)
    except Exception as exc:
        _LOGGER.debug("voice-local retain skip: %s", exc)

    return spoken