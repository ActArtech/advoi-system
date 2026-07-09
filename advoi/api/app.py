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
from fastapi.responses import Response
from pydantic import BaseModel, Field

from advoi import __version__
from advoi.cache.agent_cache import agents_status_summary
from advoi.routing.agent_bootstrap import prewarm_all_agents
from advoi.decision.frames import FRAMES
from advoi.llm.openrouter import resolve_llm_credentials
from advoi.routing.agents import AGENTS
from advoi.routing.frame_runner import frame_to_dict, run_frame
from advoi.routing.intent import frame_intent_label, resolve_voice_action
from advoi.routing.orchestrator import run_frames_parallel, systems_for_frame
from advoi.voice.livekit_env import public_livekit_url
from advoi.guardian.confirmation import frame_needs_confirmation, global_confirmation_enabled
from advoi.observability.otel_setup import setup_otel
from advoi.observability.request_trace import RequestTraceMiddleware
from advoi.aether.service import get_aether_service
from advoi.voice.respond import warm_spoken_reply
from advoi.voice.server_tts import synthesize_speech
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
setup_otel(app, service_name="advoi-api")

_origins = os.getenv("ADVOI_ALLOWED_ORIGINS", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestTraceMiddleware)


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
    aether = get_aether_service()
    return {
        "room": default_room_name(),
        "memory_provider": os.getenv("MEMORY_PROVIDER", "hindsight"),
        "letta_enabled": os.getenv("LETTA_ENABLED", "false").lower() == "true",
        "confirmation_required": os.getenv("ADVOI_CONFIRMATION_REQUIRED", "true").lower() == "true",
        "frames": [frame_to_dict(f) for f in FRAMES],
        "agents": [
            {"id": a.id, "name": a.name, "role": a.role}
            for a in AGENTS.values()
        ],
        "aether": await aether.portfolio(),
    }


class FrameRunRequest(BaseModel):
    confirmed: bool = False
    refresh: bool = False


class FrameRunResponse(BaseModel):
    frame_id: str
    agent_id: str
    agent_name: str | None = None
    status: str
    spoken_summary: str
    agents_used: list[str] = Field(default_factory=list)
    systems: list[str] = Field(default_factory=list)
    detail: dict[str, Any] = Field(default_factory=dict)


def _frame_run_response(result) -> FrameRunResponse:
    agent = AGENTS.get(result.agent_id)
    return FrameRunResponse(
        frame_id=result.frame_id,
        agent_id=result.agent_id,
        agent_name=agent.name if agent else None,
        status=result.status,
        spoken_summary=result.spoken_summary,
        agents_used=list(result.detail.get("agents_used") or [result.agent_id]),
        systems=systems_for_frame(result.frame_id),
        detail=result.detail,
    )


@app.get("/api/frames")
async def list_frames() -> dict[str, Any]:
    return {"frames": [frame_to_dict(f) for f in FRAMES]}


@app.get("/api/review-queue")
async def review_queue_pending() -> dict[str, Any]:
    from advoi.memory.review_queue import list_pending

    items = await list_pending()
    return {"pending": items, "count": len(items)}


@app.get("/api/review-queue/{queue_id}")
async def review_queue_item(queue_id: int) -> dict[str, Any]:
    from advoi.memory.review_queue import get_review_item

    item = await get_review_item(queue_id)
    if not item:
        raise HTTPException(status_code=404, detail="Review queue item not found")
    return {"item": item}


@app.get("/api/agents")
async def list_agents() -> dict[str, Any]:
    return agents_status_summary()


@app.post("/api/agents/prewarm")
async def prewarm_agents() -> dict[str, Any]:
    results = await prewarm_all_agents()
    summary = agents_status_summary()
    return {"prewarmed": len(results), **summary}


@app.get("/api/agents/control")
async def agents_control_status() -> dict[str, Any]:
    from advoi.routing.agent_control import daemon_control_status

    return daemon_control_status()


@app.post("/api/agents/stop")
async def stop_agents(body: FrameRunRequest | None = None) -> dict[str, Any]:
    from advoi.routing.agent_control import spoken_stop_agents, stop_agent_daemons

    confirmed = True if body is None else body.confirmed
    if os.getenv("ADVOI_CONFIRMATION_REQUIRED", "true").lower() in {"1", "true", "yes"}:
        if not confirmed:
            return {
                "ok": False,
                "status": "confirmation_required",
                "spoken_summary": "Say stop agents confirm to pause background daemons.",
            }
    result = await stop_agent_daemons()
    return {**result, "spoken_summary": spoken_stop_agents(result)}


@app.post("/api/agents/restart")
async def restart_agents() -> dict[str, Any]:
    from advoi.routing.agent_control import restart_agent_daemons, spoken_restart_agents

    result = await restart_agent_daemons()
    return {**result, "spoken_summary": spoken_restart_agents(result)}


class VoiceRespondRequest(BaseModel):
    transcript: str
    recent_phrases: list[str] = Field(default_factory=list)
    session_id: str | None = None


class VoiceRespondResponse(BaseModel):
    spoken: str
    action: str = "chat"
    agent_id: str | None = None
    agent_name: str | None = None
    frame_id: str | None = None
    agents_used: list[str] = Field(default_factory=list)
    systems: list[str] = Field(default_factory=list)


class VoiceSpeakRequest(BaseModel):
    text: str
    voice: str | None = None


class OrchestrateRequest(BaseModel):
    frame_ids: list[str] = Field(default_factory=list)
    confirmed: bool = False
    refresh: bool = False


class OrchestrateResponse(BaseModel):
    results: list[FrameRunResponse]
    agents_used: list[str] = Field(default_factory=list)
    systems: list[str] = Field(default_factory=list)
    spoken_summary: str = ""


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


@app.get("/api/capabilities")
async def capabilities_catalog() -> dict[str, Any]:
    from advoi.voice.capabilities import build_capabilities_payload

    return build_capabilities_payload()


@app.post("/api/voice/intent", response_model=VoiceIntentResponse)
async def voice_intent(body: VoiceIntentRequest) -> VoiceIntentResponse:
    from advoi.voice.capabilities import classify_operator_intent

    op = classify_operator_intent(body.transcript)
    if op:
        return VoiceIntentResponse(
            transcript=body.transcript,
            action=op,
            frame_id=None,
            frame_label=None,
            confirmed=None,
            preview=None,
        )

    action = resolve_voice_action(body.transcript)
    frame_id = action.get("frame_id") if action["action"] == "frame" else None
    confirmed = action.get("confirmed") if action["action"] == "frame" else None
    preview: FrameRunResponse | None = None

    if body.preview and frame_id:
        try:
            result = await run_frame(frame_id, confirmed=bool(confirmed))
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        preview = _frame_run_response(result)

    return VoiceIntentResponse(
        transcript=body.transcript,
        action=action["action"],
        frame_id=frame_id,
        frame_label=frame_intent_label(frame_id) if frame_id else None,
        confirmed=confirmed,
        preview=preview,
    )


@app.post("/api/voice/speak")
async def voice_speak(body: VoiceSpeakRequest) -> Response:
    """Server-side TTS (OpenAI-compatible). Avoids browser WebGPU/WASM models."""
    try:
        audio = await synthesize_speech(body.text, voice=body.voice)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"TTS request failed: {exc}") from exc
    return Response(content=audio, media_type="audio/mpeg")


@app.post("/api/voice/respond", response_model=VoiceRespondResponse)
async def voice_respond(body: VoiceRespondRequest) -> VoiceRespondResponse:
    try:
        reply = await warm_spoken_reply(
            body.transcript,
            recent_phrases=body.recent_phrases,
            session_id=body.session_id or "voice-local",
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"LLM request failed: {exc}") from exc
    return VoiceRespondResponse(
        spoken=reply.spoken,
        action=reply.action,
        agent_id=reply.agent_id,
        agent_name=reply.agent_name,
        frame_id=reply.frame_id,
        agents_used=reply.agents_used,
        systems=reply.systems,
    )


@app.post("/api/agents/orchestrate", response_model=OrchestrateResponse)
async def orchestrate_agents(body: OrchestrateRequest) -> OrchestrateResponse:
    frame_ids = body.frame_ids or ["fleet_status", "open_briefs"]
    try:
        results = await run_frames_parallel(
            frame_ids,  # type: ignore[arg-type]
            confirmed=body.confirmed,
            refresh=body.refresh,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if not results:
        raise HTTPException(status_code=400, detail="No valid frame ids provided")

    agents_used: list[str] = []
    systems: set[str] = set()
    spoken_parts: list[str] = []
    rows: list[FrameRunResponse] = []
    for result in results:
        agents_used.extend(result.detail.get("agents_used") or [result.agent_id])
        systems.update(systems_for_frame(result.frame_id))
        spoken_parts.append(result.spoken_summary)
        rows.append(_frame_run_response(result))

    deduped_agents = list(dict.fromkeys(agents_used))
    return OrchestrateResponse(
        results=rows,
        agents_used=deduped_agents,
        systems=sorted(systems),
        spoken_summary=" ".join(spoken_parts),
    )


@app.post("/api/agents/run-all", response_model=OrchestrateResponse)
@app.post("/api/agents/run-six", response_model=OrchestrateResponse)
async def run_all_agents(
    refresh: bool = False,
    confirmed: bool = True,
) -> OrchestrateResponse:
    """Run all six specialist frames in parallel."""
    frame_ids = [f.id for f in FRAMES]
    results = await run_frames_parallel(
        frame_ids,  # type: ignore[arg-type]
        confirmed=confirmed,
        refresh=refresh,
    )
    agents_used: list[str] = []
    systems: set[str] = set()
    spoken_parts: list[str] = []
    rows: list[FrameRunResponse] = []
    for result in results:
        agents_used.extend(result.detail.get("agents_used") or [result.agent_id])
        systems.update(systems_for_frame(result.frame_id))
        spoken_parts.append(result.spoken_summary)
        rows.append(_frame_run_response(result))

    deduped_agents = list(dict.fromkeys(agents_used))
    return OrchestrateResponse(
        results=rows,
        agents_used=deduped_agents,
        systems=sorted(systems),
        spoken_summary=" ".join(spoken_parts),
    )


@app.get("/api/diagnostics/agents")
async def agents_diagnostics() -> dict[str, Any]:
    summary = agents_status_summary()
    return {
        "ok": summary["all_ready"],
        "stage": "multi-agent-6",
        **summary,
    }


@app.get("/api/diagnostics/memory")
async def memory_diagnostics() -> dict[str, Any]:
    """Memory stack readiness — Letta, operational store, Redis, Postgres hints."""
    from advoi.memory.operational_bridge import operational_diagnostics
    from advoi.memory.router import load_memory_config

    cfg = load_memory_config()
    store_path = os.getenv("ADVOI_OPERATIONAL_STORE", "data/operational-memory.jsonl")
    store_exists = os.path.isfile(store_path)
    op = await operational_diagnostics()
    return {
        "ok": True,
        "provider": cfg.provider,
        "hindsight_enabled": cfg.hindsight_enabled,
        "letta_enabled": cfg.letta_enabled,
        "letta_base_url": bool(cfg.letta_base_url),
        **op,
        "operational_store_enabled": os.getenv(
            "ADVOI_OPERATIONAL_STORE_ENABLED", "true"
        ).lower()
        in {"1", "true", "yes"},
        "operational_store_path": store_path,
        "operational_store_exists": store_exists,
        "redis_configured": bool(cfg.redis_url),
        "postgres_configured": bool(cfg.database_url),
    }


@app.get("/api/aether/portfolio")
async def aether_portfolio() -> dict[str, Any]:
    return await get_aether_service().portfolio()


@app.get("/api/aether/gate")
async def aether_gate() -> dict[str, Any]:
    return await get_aether_service().gate()


@app.get("/api/aether/routes")
async def aether_routes() -> dict[str, Any]:
    return get_aether_service().routes()


@app.get("/api/aether/ventures/{venture_id}")
async def aether_venture(venture_id: str) -> dict[str, Any]:
    row = await get_aether_service().venture(venture_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Unknown venture: {venture_id}")
    return row


@app.post("/api/aether/reload")
async def aether_reload_portfolio() -> dict[str, Any]:
    return get_aether_service().reload()


@app.get("/api/aether/status")
async def aether_status() -> dict[str, Any]:
    from advoi.memory.operational_bridge import operational_diagnostics

    status = get_aether_service().status()
    status["memory"] = await operational_diagnostics()
    return status


@app.get("/api/diagnostics/guardian")
async def guardian_diagnostics() -> dict[str, Any]:
    """Confirmation policy and frame risk summary."""
    frames = [
        {
            "frame_id": f.id,
            "requires_confirmation": frame_needs_confirmation(f.id),
        }
        for f in FRAMES
    ]
    return {
        "ok": True,
        "confirmation_enabled": global_confirmation_enabled(),
        "frames": frames,
        "high_risk_frames": [row["frame_id"] for row in frames if row["requires_confirmation"]],
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
    return _frame_run_response(result)


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
        reply = await warm_spoken_reply("fleet status please", session_id="latency-probe")
        respond_ms = round((time.perf_counter() - started) * 1000, 1)
        return {
            "respond_ms": respond_ms,
            "respond_chars": len(reply.spoken or ""),
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