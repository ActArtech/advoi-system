"""Server-side TTS — OpenAI-compatible speech API (no browser WebGPU/WASM)."""

from __future__ import annotations

import logging
import os

import httpx

from advoi.llm.openrouter import resolve_llm_credentials

_LOGGER = logging.getLogger(__name__)

DEFAULT_VOICE = "alloy"


async def synthesize_speech(text: str, *, voice: str | None = None) -> bytes:
    """Return MP3 audio bytes for the given text."""
    spoken = (text or "").strip()
    if not spoken:
        raise ValueError("text is required")

    creds = resolve_llm_credentials()
    base_url = (creds.base_url or "https://api.openai.com/v1").rstrip("/")
    voice_id = (voice or os.getenv("OPENAI_TTS_VOICE", DEFAULT_VOICE)).strip() or DEFAULT_VOICE

    headers = {"Authorization": f"Bearer {creds.api_key}"}
    if creds.provider == "openrouter":
        headers["HTTP-Referer"] = "https://advoi.keyteller.com"
        headers["X-Title"] = "ADVoi server voice"

    payload = {
        "model": creds.tts_model,
        "input": spoken[:4096],
        "voice": voice_id,
        "response_format": "mp3",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{base_url}/audio/speech",
            headers=headers,
            json=payload,
        )
        if resp.status_code >= 400:
            _LOGGER.warning("server TTS failed status=%s body=%s", resp.status_code, resp.text[:200])
        resp.raise_for_status()
        return resp.content