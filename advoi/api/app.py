"""ADVoi HTTP API — health, LiveKit tokens, session metadata."""

from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from advoi import __version__
from advoi.cache.agent_cache import agents_status_summary
from advoi.routing.agent_bootstrap import prewarm_all_agents
from advoi.decision.frames import FRAMES
from advoi.llm.openrouter import resolve_llm_credentials
from advoi.routing.agents import AGENTS
from advoi.routing.frame_runner import frame_to_dict, run_frame
from advoi.routing.intent import frame_intent_label, resolve_voice_action
from advoi.voice.livekit_env import public_livekit_url
from advoi.voice.respond import warm_spoken_reply
from advoi.voice.tokens import default_room_name, mint_room_token


def _prewarm_enabled() -> bool:
    return os.getenv("ADVOI_PREWARM_AGENTS", "true").lower() in {"1", "true", "yes"}


@asynccontextmanager
async def _lifespan(app: FastAPI):  # noqa: ARG001
    if _prewarm_enabled():
        try:
            await prewarm_all_agents()
        except Exception:
            pass
    yield


app = FastAPI(title="ADVoi API", version=__version__, lifespan=_lifespan)

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
    summary = agents_status_summary()
    return {
        "ok": True,
        "service": "advoi-api",
        "version": __version__,
        "stage": "voice-pwa-2",
        "agents_ready": summary["ready"],
        "agents_total": summary["total"],
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
    refresh: bool = False


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
    return agents_status_summary()


@app.post("/api/agents/prewarm")
async def prewarm_agents() -> dict[str, Any]:
    results = await prewarm_all_agents()
    summary = agents_status_summary()
    return {"prewarmed": len(results), **summary}


class VoiceRespondRequest(BaseModel):
    transcript: str
    recent_phrases: list[str] = Field(default_factory=list)
    session_id: str | None = None


class VoiceRespondResponse(BaseModel):
    spoken: str


class VoiceIntentRequest(BaseModel):
    transcript: str
    preview: bool = False


class VoiceIntentResponse(BaseModel):
    transcript: str
    action: str
    frame_id: str | None = None
    frame_label: str | None = None
    confirmed: bool | None = None
    preview: FrameRunResponse | None = None


@app.post("/api/voice/intent", response_model=VoiceIntentResponse)
async def voice_intent(body: VoiceIntentRequest) -> VoiceIntentResponse:
    action = resolve_voice_action(body.transcript)
    frame_id = action.get("frame_id") if action["action"] == "frame" else None
    confirmed = action.get("confirmed") if action["action"] == "frame" else None
    preview: FrameRunResponse | None = None

    if body.preview and frame_id:
        try:
            result = await run_frame(frame_id, confirmed=bool(confirmed))
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        preview = FrameRunResponse(
            frame_id=result.frame_id,
            agent_id=result.agent_id,
            status=result.status,
            spoken_summary=result.spoken_summary,
            detail=result.detail,
        )

    return VoiceIntentResponse(
        transcript=body.transcript,
        action=action["action"],
        frame_id=frame_id,
        frame_label=frame_intent_label(frame_id) if frame_id else None,
        confirmed=confirmed,
        preview=preview,
    )


@app.post("/api/voice/respond", response_model=VoiceRespondResponse)
async def voice_respond(body: VoiceRespondRequest) -> VoiceRespondResponse:
    try:
        spoken = await warm_spoken_reply(
            body.transcript,
            recent_phrases=body.recent_phrases,
            session_id=body.session_id or "voice-local",
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"LLM request failed: {exc}") from exc
    return VoiceRespondResponse(spoken=spoken)


@app.get("/api/diagnostics/agents")
async def agents_diagnostics() -> dict[str, Any]:
    summary = agents_status_summary()
    return {
        "ok": summary["all_ready"],
        "stage": "multi-agent-1",
        **summary,
    }


@app.post("/api/frames/{frame_id}/run", response_model=FrameRunResponse)
async def run_decision_frame(
    frame_id: str,
    body: FrameRunRequest | None = None,
    refresh: bool = False,
) -> FrameRunResponse:
    req = body or FrameRunRequest()
    try:
        result = await run_frame(
            frame_id,
            confirmed=req.confirmed,
            refresh=refresh or req.refresh,
        )
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
        "memory_provider": os.getenv("MEMORY_PROVIDER", "hindsight"),
        "voice_respond_ready": False,
    }
    try:
        creds = resolve_llm_credentials()
        checks["llm_provider"] = creds.provider
        checks["llm_model"] = creds.llm_model
        checks["llm_key"] = True
        checks["voice_respond_ready"] = True
    except RuntimeError:
        checks["llm_key"] = False

    voice_mode = os.getenv("ADVOI_VOICE_MODE", "livekit").lower()
    if voice_mode == "local":
        ok = checks["voice_respond_ready"]
    else:
        ok = checks["livekit_url"] and checks["livekit_keys"] and checks["llm_key"]
    return {
        "ok": ok,
        "stage": "voice-pwa-2",
        "voice_mode": voice_mode,
        "checks": checks,
        "room": default_room_name(),
    }