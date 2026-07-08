"""ADVoi HTTP API — health, LiveKit tokens, session metadata."""

from __future__ import annotations

import os
import time
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


@app.get("/api/review-queue")
async def review_queue_pending() -> dict[str, Any]:
    from advoi.memory.review_queue import list_pending

    items = await list_pending()
    return {"pending": items, "count": len(items)}


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


async def _probe_memory_bridge() -> dict[str, Any]:
    """Check Hindsight HTTP bridge reachability (short timeout, non-blocking)."""
    url = os.getenv("HINDSIGHT_BRIDGE_URL", "").rstrip("/")
    if not url:
        return {"memory_bridge_ok": False, "memory_bridge_mode": "mock"}

    timeout = httpx.Timeout(2.0, connect=1.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            health = await client.get(f"{url}/health")
            health.raise_for_status()
            return {"memory_bridge_ok": True, "memory_bridge_mode": "hermes"}
    except Exception:
        return {"memory_bridge_ok": False, "memory_bridge_mode": "unavailable"}


async def _measure_frame_latency_ms(frame_id: str = "fleet_status") -> dict[str, Any]:
    """Time one mock or live frame run for latency hints in diagnostics."""
    try:
        started = time.perf_counter()
        result = await run_frame(frame_id)
        return {
            "frame_run_ms": round((time.perf_counter() - started) * 1000, 1),
            "frame_id": frame_id,
            "frame_status": result.status,
        }
    except Exception as exc:
        return {
            "frame_run_ms": None,
            "frame_id": frame_id,
            "frame_error": str(exc),
        }


async def _voice_diagnostics_payload() -> dict[str, Any]:
    """Build voice journey diagnostics without joining a LiveKit room."""
    checks: dict[str, Any] = {
        "livekit_url": bool(public_livekit_url()),
        "livekit_keys": bool(os.getenv("LIVEKIT_API_KEY") and os.getenv("LIVEKIT_API_SECRET")),
        "frames": len(FRAMES),
        "agents": len(AGENTS),
        "memory_provider": os.getenv("MEMORY_PROVIDER", "hindsight"),
        "voice_respond_ready": False,
        "llm_key": False,
    }
    warnings: list[str] = []
    llm_key = False

    try:
        creds = resolve_llm_credentials()
        checks["llm_provider"] = creds.provider
        checks["llm_model"] = creds.llm_model
        checks["llm_key"] = True
        checks["voice_respond_ready"] = True
        llm_key = True
    except RuntimeError:
        checks["llm_key_required"] = True
        warnings.append(
            "OPENROUTER_API_KEY or OPENAI_API_KEY is required; advoi-voice exits at startup without it."
        )

    voice_mode = os.getenv("ADVOI_VOICE_MODE", "livekit").lower()
    if voice_mode == "local":
        ok = checks["voice_respond_ready"]
    else:
        ok = bool(checks["livekit_url"] and checks["livekit_keys"] and llm_key)

    reason: str | None = None
    if not ok:
        reasons: list[str] = []
        if voice_mode != "local" and not checks["livekit_url"]:
            reasons.append("LIVEKIT_URL is not set")
        if voice_mode != "local" and not checks["livekit_keys"]:
            reasons.append("LIVEKIT_API_KEY and LIVEKIT_API_SECRET are required")
        if not llm_key:
            reasons.append("OPENROUTER_API_KEY or OPENAI_API_KEY is required for voice")
        if voice_mode == "local" and not checks["voice_respond_ready"]:
            reasons.append("voice respond is not ready (missing LLM API key)")
        reason = "; ".join(reasons) if reasons else "voice diagnostics failed"

    voice_agent_hint = (
        "advoi-voice (Pipecat + LiveKit) needs OPENROUTER_API_KEY or OPENAI_API_KEY for "
        "STT, LLM, and TTS. Set keys in deploy/.env and restart the advoi-voice container."
        if not llm_key
        else "advoi-voice has LLM credentials configured for STT, LLM, and TTS."
    )

    memory_bridge = await _probe_memory_bridge()
    checks.update(memory_bridge)

    if memory_bridge["memory_bridge_mode"] == "unavailable":
        warnings.append("Memory bridge down — frames use mock cache (non-fatal)")

    latency = await _measure_frame_latency_ms()
    if latency.get("frame_run_ms") is not None:
        checks["frame_run_ms"] = latency["frame_run_ms"]

    return {
        "ok": ok,
        "reason": reason,
        "stage": "voice-pwa-2",
        "voice_mode": voice_mode,
        "checks": checks,
        "warnings": warnings,
        "voice_agent_hint": voice_agent_hint,
        "room": default_room_name(),
        "latency": latency,
    }


@app.get("/api/diagnostics/voice")
async def voice_diagnostics() -> dict[str, Any]:
    """Journey-test endpoint — checks config without joining a LiveKit room."""
    return await _voice_diagnostics_payload()


def _latency_sla_ms() -> float:
    raw = os.getenv("ADVOI_LATENCY_SLA_MS", "800")
    try:
        return max(100.0, float(raw))
    except ValueError:
        return 800.0


async def _measure_intent_latency_ms() -> dict[str, Any]:
    """Time classify + optional preview frame for voice intent path."""
    transcript = "give me a fleet status update"
    try:
        started = time.perf_counter()
        action = resolve_voice_action(transcript)
        intent_ms = round((time.perf_counter() - started) * 1000, 1)
        preview_ms: float | None = None
        if action.get("action") == "frame" and action.get("frame_id"):
            started = time.perf_counter()
            result = await run_frame(action["frame_id"], confirmed=bool(action.get("confirmed")))
            preview_ms = round((time.perf_counter() - started) * 1000, 1)
            return {
                "intent_ms": intent_ms,
                "intent_preview_ms": preview_ms,
                "intent_frame_id": action["frame_id"],
                "intent_status": result.status,
            }
        return {"intent_ms": intent_ms, "intent_preview_ms": None, "intent_frame_id": None}
    except Exception as exc:
        return {"intent_ms": None, "intent_preview_ms": None, "intent_error": str(exc)}


async def _measure_respond_latency_ms() -> dict[str, Any]:
    """Time warm_spoken_reply on a frame-routed transcript (mock-friendly)."""
    try:
        started = time.perf_counter()
        spoken = await warm_spoken_reply("fleet status please", session_id="latency-probe")
        respond_ms = round((time.perf_counter() - started) * 1000, 1)
        return {
            "respond_ms": respond_ms,
            "respond_chars": len(spoken or ""),
        }
    except Exception as exc:
        return {"respond_ms": None, "respond_error": str(exc)}


@app.get("/api/diagnostics/latency")
async def latency_diagnostics() -> dict[str, Any]:
    """Quick timing probe: health, token mint, frame, intent, and respond paths."""
    timings_ms: dict[str, float | None] = {}
    sla_ms = _latency_sla_ms()

    started = time.perf_counter()
    health_payload = await health()
    timings_ms["health_ms"] = round((time.perf_counter() - started) * 1000, 1)

    started = time.perf_counter()
    token_ok = False
    try:
        mint_room_token(
            room_name=default_room_name(),
            identity="latency-probe",
            name="Latency probe",
        )
        token_ok = True
        timings_ms["token_ms"] = round((time.perf_counter() - started) * 1000, 1)
    except Exception:
        timings_ms["token_ms"] = None

    frame_latency = await _measure_frame_latency_ms()
    timings_ms["frame_run_ms"] = frame_latency.get("frame_run_ms")

    intent_latency = await _measure_intent_latency_ms()
    timings_ms["intent_ms"] = intent_latency.get("intent_ms")
    timings_ms["intent_preview_ms"] = intent_latency.get("intent_preview_ms")

    respond_latency = await _measure_respond_latency_ms()
    timings_ms["respond_ms"] = respond_latency.get("respond_ms")

    api_path_ms: float | None = None
    parts = [
        timings_ms.get("intent_ms"),
        timings_ms.get("intent_preview_ms") or timings_ms.get("frame_run_ms"),
    ]
    if all(p is not None for p in parts):
        api_path_ms = round(float(parts[0]) + float(parts[1]), 1)  # type: ignore[arg-type]
    timings_ms["api_voice_path_ms"] = api_path_ms

    sla_ok = api_path_ms is not None and api_path_ms <= sla_ms

    return {
        "ok": bool(
            health_payload.get("ok")
            and token_ok
            and timings_ms.get("frame_run_ms") is not None
            and timings_ms.get("intent_ms") is not None
            and timings_ms.get("respond_ms") is not None
        ),
        "stage": "voice-pwa-2",
        "timings_ms": timings_ms,
        "sla_target_ms": sla_ms,
        "sla_ok": sla_ok,
        "sla_scope": "API intent + frame preview only; full mic-STT-TTS round trip not measured here",
        "frame_id": frame_latency.get("frame_id", "fleet_status"),
        "frame_status": frame_latency.get("frame_status"),
        "intent_frame_id": intent_latency.get("intent_frame_id"),
        "respond_chars": respond_latency.get("respond_chars"),
    }