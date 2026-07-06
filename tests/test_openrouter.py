import pytest

from advoi.llm.openrouter import OPENROUTER_DEFAULT_BASE_URL, resolve_llm_credentials


def test_prefers_openrouter_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    creds = resolve_llm_credentials(
        openrouter_api_key="or-key",
        default_model="gpt-4o-mini",
    )
    assert creds.provider == "openrouter"
    assert creds.api_key == "or-key"
    assert creds.base_url == OPENROUTER_DEFAULT_BASE_URL
    assert creds.llm_model == "openai/gpt-4o-mini"
    assert creds.stt_model == "openai/gpt-4o-mini-transcribe"
    assert creds.tts_model == "openai/tts-1"


def test_openrouter_model_already_prefixed():
    creds = resolve_llm_credentials(
        openrouter_api_key="or-key",
        default_model="anthropic/claude-3.5-sonnet",
    )
    assert creds.llm_model == "anthropic/claude-3.5-sonnet"


def test_falls_back_to_openai(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    creds = resolve_llm_credentials(openai_api_key="sk-test", default_model="openai/gpt-4o-mini")
    assert creds.provider == "openai"
    assert creds.base_url is None
    assert creds.llm_model == "gpt-4o-mini"


def test_requires_some_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY or OPENAI_API_KEY"):
        resolve_llm_credentials()