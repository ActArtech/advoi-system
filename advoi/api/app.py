"""ADVoi HTTP API — health, LiveKit tokens, session metadata."""

from __future__ import annotations

import os
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from advoi import __version__
from advoi.decision.frames import FRAMES
from advoi.llm.openrouter import resolve_llm_credentials
from advoi.routing.agents import AGENTS
from advoi.routing.frame_runner import frame_to_dict, run_frame
from advoi.voice.livekit_env import public_livekit_url
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
@app.get("/api/health")
async def health() -> dict[str, Any]:
    return {
        "ok": True,
        "service": "advoi-api",
        "version": __version__,
        "stage": "voice-pwa-2",
    }


@app.post("/api/livekit/token", response_model=LiveKitTokenResponse)
async def livekit_token(body: LiveKitTokenRequest | None = None) -> LiveKitTokenResponse:
    url = public_livekit_url()

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
        "frames": [frame_to_dict(f) for f in FRAMES],
        "agents": [
            {"id": a.id, "name": a.name, "role": a.role}
            for a in AGENTS.values()
        ],
    }


class FrameRunRequest(BaseModel):
    confirmed: bool = False


class FrameRunResponse(BaseModel):
    frame_id: str
    agent_id: str
    status: str
    spoken_summary: str
    detail: dict[str, Any] = Field(default_factory=dict)


@app.get("/api/frames")
async def list_frames() -> dict[str, Any]:
    return {"frames": [frame_to_dict(f) for f in FRAMES]}


@app.get("/api/agents")
async def list_agents() -> dict[str, Any]:
    return {
        "agents": [
            {"id": a.id, "name": a.name, "role": a.role, "speaks_first": a.speaks_first}
            for a in AGENTS.values()
        ]
    }


@app.post("/api/frames/{frame_id}/run", response_model=FrameRunResponse)
async def run_decision_frame(frame_id: str, body: FrameRunRequest | None = None) -> FrameRunResponse:
    req = body or FrameRunRequest()
    try:
        result = await run_frame(frame_id, confirmed=req.confirmed)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FrameRunResponse(
        frame_id=result.frame_id,
        agent_id=result.agent_id,
        status=result.status,
        spoken_summary=result.spoken_summary,
        detail=result.detail,
    )


@app.get("/api/diagnostics/voice")
async def voice_diagnostics() -> dict[str, Any]:
    """Journey-test endpoint — checks config without joining a LiveKit room."""
    checks: dict[str, Any] = {
        "livekit_url": bool(public_livekit_url()),
        "livekit_keys": bool(os.getenv("LIVEKIT_API_KEY") and os.getenv("LIVEKIT_API_SECRET")),
        "frames": len(FRAMES),
        "agents": len(AGENTS),
    }
    try:
        creds = resolve_llm_credentials()
        checks["llm_provider"] = creds.provider
        checks["llm_model"] = creds.llm_model
        checks["llm_key"] = True
    except RuntimeError:
        checks["llm_key"] = False

    ok = checks["livekit_url"] and checks["livekit_keys"] and checks["llm_key"]
    return {
        "ok": ok,
        "stage": "voice-pwa-2",
        "checks": checks,
        "room": default_room_name(),
    }