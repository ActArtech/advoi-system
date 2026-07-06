"""ADVoi HTTP API — health, LiveKit tokens, session metadata."""

from __future__ import annotations

import os
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from advoi import __version__
from advoi.voice.tokens import default_room_name, mint_room_token

app = FastAPI(title="ADVoi API", version=__version__)

_origins = os.getenv("ADVOI_ALLOWED_ORIGINS", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LiveKitTokenRequest(BaseModel):
    room_name: str | None = None
    identity: str | None = None
    name: str | None = None


class LiveKitTokenResponse(BaseModel):
    token: str
    url: str
    room_name: str
    identity: str


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "ok": True,
        "service": "advoi-api",
        "version": __version__,
        "stage": "voice-pwa-1",
    }


@app.post("/api/livekit/token", response_model=LiveKitTokenResponse)
async def livekit_token(body: LiveKitTokenRequest | None = None) -> LiveKitTokenResponse:
    url = os.getenv("LIVEKIT_URL", "")
    if not url:
        raise HTTPException(status_code=503, detail="LIVEKIT_URL not configured")

    req = body or LiveKitTokenRequest()
    room = req.room_name or default_room_name()
    identity = req.identity or f"user-{uuid.uuid4().hex[:12]}"
    try:
        token = mint_room_token(room_name=room, identity=identity, name=req.name or "You")
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return LiveKitTokenResponse(token=token, url=url, room_name=room, identity=identity)


@app.get("/api/session")
async def session_info() -> dict[str, Any]:
    return {
        "room": default_room_name(),
        "memory_provider": os.getenv("MEMORY_PROVIDER", "hindsight"),
        "confirmation_required": os.getenv("ADVOI_CONFIRMATION_REQUIRED", "true").lower() == "true",
    }