"""LiveKit URL and key resolution — self-hosted dev server by default."""

from __future__ import annotations

import os

# livekit-server --dev defaults (https://docs.livekit.io/transport/self-hosting/local/)
LIVEKIT_DEV_KEY = "devkey"
LIVEKIT_DEV_SECRET = "secret"


def use_dev_keys() -> bool:
    explicit = os.getenv("LIVEKIT_USE_DEV_KEYS", "").strip().lower()
    if explicit in {"0", "false", "no"}:
        return False
    if explicit in {"1", "true", "yes"}:
        return True
    key = os.getenv("LIVEKIT_API_KEY", "").strip()
    secret = os.getenv("LIVEKIT_API_SECRET", "").strip()
    return not key or not secret


def resolve_api_key() -> str:
    key = os.getenv("LIVEKIT_API_KEY", "").strip()
    if key:
        return key
    if use_dev_keys():
        return LIVEKIT_DEV_KEY
    return ""


def resolve_api_secret() -> str:
    secret = os.getenv("LIVEKIT_API_SECRET", "").strip()
    if secret:
        return secret
    if use_dev_keys():
        return LIVEKIT_DEV_SECRET
    return ""


def public_livekit_url() -> str:
    """WSS URL returned to browsers (via /api/livekit/token)."""
    url = os.getenv("LIVEKIT_URL", "").strip()
    if url:
        return url
    host = os.getenv("LIVEKIT_HOST", "").strip()
    if host:
        return f"wss://{host}"
    return "ws://127.0.0.1:7880"


def internal_livekit_url() -> str:
    """WS URL for advoi-voice inside the compose network."""
    return os.getenv("LIVEKIT_INTERNAL_URL", "ws://livekit:7880").strip()