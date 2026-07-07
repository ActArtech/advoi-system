import os

import pytest

from advoi.voice.livekit_env import (
    LIVEKIT_DEV_KEY,
    LIVEKIT_DEV_SECRET,
    internal_livekit_url,
    public_livekit_url,
    resolve_api_key,
    resolve_api_secret,
    use_dev_keys,
)


def test_dev_keys_when_unset(monkeypatch):
    monkeypatch.delenv("LIVEKIT_API_KEY", raising=False)
    monkeypatch.delenv("LIVEKIT_API_SECRET", raising=False)
    monkeypatch.setenv("LIVEKIT_USE_DEV_KEYS", "true")
    assert use_dev_keys() is True
    assert resolve_api_key() == LIVEKIT_DEV_KEY
    assert resolve_api_secret() == LIVEKIT_DEV_SECRET


def test_explicit_keys_override_dev(monkeypatch):
    monkeypatch.setenv("LIVEKIT_API_KEY", "mykey")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "mysecret")
    assert use_dev_keys() is False
    assert resolve_api_key() == "mykey"


def test_public_url_from_host(monkeypatch):
    monkeypatch.delenv("LIVEKIT_URL", raising=False)
    monkeypatch.setenv("LIVEKIT_HOST", "livekit.example.com")
    assert public_livekit_url() == "wss://livekit.example.com"


def test_internal_url_default():
    assert internal_livekit_url() == "ws://livekit:7880"