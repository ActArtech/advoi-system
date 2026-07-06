"""OpenAI-compatible credentials — OpenRouter first, direct OpenAI fallback.

Mirrors clapart's ``make_openrouter_llm_call()`` pattern:
``OPENROUTER_API_KEY`` + ``https://openrouter.ai/api/v1`` with ``provider/model`` ids.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

OPENROUTER_DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"

Provider = Literal["openrouter", "openai"]


@dataclass(frozen=True)
class LLMCredentials:
    api_key: str
    base_url: str | None
    provider: Provider
    llm_model: str
    stt_model: str
    tts_model: str


def _strip(value: str | None) -> str:
    return (value or "").strip()


def _openrouter_model(model: str) -> str:
    """Ensure OpenRouter model ids include a provider prefix."""
    name = _strip(model) or "openai/gpt-4o-mini"
    if "/" in name:
        return name
    return f"openai/{name}"


def _direct_openai_model(model: str) -> str:
    name = _strip(model) or "gpt-4o-mini"
    if name.startswith("openai/"):
        return name.split("/", 1)[1]
    return name


def resolve_llm_credentials(
    *,
    openrouter_api_key: str | None = None,
    openai_api_key: str | None = None,
    openrouter_base_url: str | None = None,
    default_model: str | None = None,
    stt_model: str | None = None,
    tts_model: str | None = None,
) -> LLMCredentials:
    """Resolve API credentials for Pipecat OpenAI-compatible services."""
    router_key = _strip(openrouter_api_key or os.getenv("OPENROUTER_API_KEY"))
    openai_key = _strip(openai_api_key or os.getenv("OPENAI_API_KEY"))
    base_url = _strip(openrouter_base_url or os.getenv("OPENROUTER_BASE_URL")) or OPENROUTER_DEFAULT_BASE_URL
    raw_model = _strip(default_model or os.getenv("DEFAULT_MODEL")) or "gpt-4o-mini"
    raw_stt = _strip(stt_model or os.getenv("OPENAI_STT_MODEL")) or "gpt-4o-mini-transcribe"
    raw_tts = _strip(tts_model or os.getenv("OPENAI_TTS_MODEL")) or "tts-1"

    if router_key:
        return LLMCredentials(
            api_key=router_key,
            base_url=base_url,
            provider="openrouter",
            llm_model=_openrouter_model(raw_model),
            stt_model=_openrouter_model(raw_stt),
            tts_model=_openrouter_model(raw_tts if raw_tts != "tts-1" else "openai/tts-1"),
        )

    if openai_key:
        return LLMCredentials(
            api_key=openai_key,
            base_url=None,
            provider="openai",
            llm_model=_direct_openai_model(raw_model),
            stt_model=_direct_openai_model(raw_stt),
            tts_model=_direct_openai_model(raw_tts),
        )

    raise RuntimeError(
        "OPENROUTER_API_KEY or OPENAI_API_KEY is required for ADVoi voice "
        "(OpenRouter preferred — same pattern as clapart voicecomp)."
    )