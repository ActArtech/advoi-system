"""LiveKit access token helpers."""

from __future__ import annotations

import os
import uuid
from datetime import timedelta

from livekit import api

from advoi.voice.livekit_env import resolve_api_key, resolve_api_secret


def mint_room_token(
    *,
    room_name: str,
    identity: str | None = None,
    name: str | None = None,
    api_key: str | None = None,
    api_secret: str | None = None,
    ttl_seconds: int = 3600,
) -> str:
    key = api_key or resolve_api_key()
    secret = api_secret or resolve_api_secret()
    if not key or not secret:
        raise ValueError(
            "LIVEKIT_API_KEY and LIVEKIT_API_SECRET are required "
            "(or enable self-hosted dev keys: LIVEKIT_USE_DEV_KEYS=true)"
        )

    ident = identity or f"user-{uuid.uuid4().hex[:12]}"
    display = name or ident

    token = (
        api.AccessToken(key, secret)
        .with_identity(ident)
        .with_name(display)
        .with_ttl(timedelta(seconds=ttl_seconds))
        .with_grants(
            api.VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
            )
        )
    )
    return token.to_jwt()


def default_room_name() -> str:
    return os.getenv("LIVEKIT_DEFAULT_ROOM", "advoi-voice")