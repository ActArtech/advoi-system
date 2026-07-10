"""ADVoi HTTP API — health, LiveKit tokens, session metadata."""

from __future__ import annotations

import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from advoi import __version__
from advoi.aether.service import get_aether_service
from advoi.analytics.pel import (
    PWA_BEACON_EVENT_TYPES,
    EventSource,
    GuardianStatus,
    append_event,
)
from advoi.cache.agent_cache import agents_status_summary
from advoi.decision.frames import FRAMES
from advoi.guardian.confirmation import (
    fleet_action_needs_confirmation,
    frame_needs_confirmation,
    global_confirmation_enabled,
    high_risk_fleet_actions,
)
from advoi.llm.openrouter import resolve_llm_credentials
from advoi.observability.otel_setup import setup_otel
from advoi.observability.request_trace import RequestTraceMiddleware
from advoi.ontology import OntologyValidationError, require_frame_id
from advoi.routing.agent_bootstrap import prewarm_all_agents
from advoi.routing.agents import AGENTS
from advoi.routing.frame_runner import frame_to_dict, run_frame
from advoi.routing.intent import frame_intent_label, resolve_voice_action
from advoi.routing.orchestrator import (
    run_all_specialist_frames,
    run_frames_parallel,
    systems_for_frame,
)
from advoi.voice.livekit_env import public_livekit_url
from advoi.voice.respond import warm_spoken_reply
from advoi.voice.server_tts import synthesize_speech
from advoi.voice.tokens import default_room_name, mint_room_token


def _prewarm_enabled() -> bool:
    return os.getenv("ADVOI_PREWARM_AGENTS", "true").lower() in {"1", "true", "yes"}


@asynccontextmanager
async def _lifespan(app: FastAPI):  # noqa: ARG001
    # Versioned SQL under deploy/migrations/ — idempotent schema_migrations tracking.
    try:
        from advoi.db.migrations import apply_pending_migrations

        await apply_pending_migrations()
    except Exception:
        pass
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


@app.exception_handler(OntologyValidationError)
async def ontology_validation_error_handler(
    _request: Request,
    exc: OntologyValidationError,
) -> JSONResponse:
    """Unregistered frame_id / agent_id → 422 with ``{detail, code}``."""
    return JSONResponse(status_code=422, content=exc.as_dict())


class LiveKitTokenRequest(BaseModel):
    room_name: str | None = None
    identity: str | None = None
    name: str | None = None


class LiveKitTokenResponse(BaseModel):
    token: str
    url: str
    room_name: str
    identity: str


class PwaBeaconEvent(BaseModel):
    """Thin PWA analytics beacon → portfolio_events (no third-party SDK)."""

    type: str = Field(
        ..., description="One of pwa_connect, frame_tap, confirm_shown, confirm_accept, error"
    )
    venture_id: str = Field(default="advoi", min_length=1, max_length=128)
    payload: dict[str, Any] = Field(default_factory=dict)
    session_id: str | None = Field(default=None, max_length=128)
    guardian_status: str | None = None
    execution_ref: str | None = Field(default=None, max_length=256)


class PwaBeaconResponse(BaseModel):
    ok: bool
    id: str | None = None
    type: str
    persisted: bool = False


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


@app.post("/api/events", response_model=PwaBeaconResponse)
async def post_portfolio_event(body: PwaBeaconEvent) -> PwaBeaconResponse:
    """Accept PWA thin-beacon payloads and append to portfolio_events (PEL).

    Allowed types: pwa_connect, frame_tap, confirm_shown, confirm_accept, error.
    Fire-and-forget friendly: always 200 when schema is valid (persisted may be false
    without DATABASE_URL / ADVOI_PEL_MEMORY).
    """
    event_type = (body.type or "").strip().lower()
    if event_type not in PWA_BEACON_EVENT_TYPES:
        allowed = ", ".join(sorted(PWA_BEACON_EVENT_TYPES))
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported event type {body.type!r}. Allowed: {allowed}",
        )

    payload = dict(body.payload or {})
    if body.session_id:
        payload.setdefault("session_id", body.session_id)
    payload.setdefault("client", "pwa")

    guardian: str | None = body.guardian_status
    if guardian is None and event_type == "confirm_shown":
        guardian = GuardianStatus.PENDING.value
    elif guardian is None and event_type == "confirm_accept":
        guardian = GuardianStatus.ALLOWED.value

    event_id = await append_event(
        venture_id=body.venture_id,
        source=EventSource.API,
        event_type=event_type,
        payload=payload,
        guardian_status=guardian,
        execution_ref=body.execution_ref,
    )
    return PwaBeaconResponse(
        ok=True,
        id=event_id,
        type=event_type,
        persisted=event_id is not None,
    )


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
        "agents": [{"id": a.id, "name": a.name, "role": a.role} for a in AGENTS.values()],
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


@app.get("/api/briefs")
async def list_open_briefs_api() -> dict[str, Any]:
    """Open decision briefs for PWA home surface (read-only; no frame run / PEL).

    Reuses Brief Curator load path: Postgres canonical → Redis cache-only fallback.
    """
    from advoi.routing.frame_runner import _load_open_briefs

    items, source = await _load_open_briefs()
    return {"briefs": items, "count": len(items), "source": source}


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


class FleetTriggerRequest(BaseModel):
    action: str
    project: str | None = None
    task: str | None = None
    confirmed: bool = False
    transcript: str | None = None
    # Optional; also accepted via Idempotency-Key header (header wins).
    # Duplicate key within 60s returns same result without re-running fm-bridge.
    idempotency_key: str | None = None


@app.post("/api/fleet/trigger")
async def fleet_trigger(
    body: FleetTriggerRequest,
    request: Request,
) -> dict[str, Any]:
    """Dispatch a FirstMate fleet action via fm-bridge.

    Idempotency (optional): send ``Idempotency-Key`` header **or** body field
    ``idempotency_key``. Same key within 60s replays the prior terminal result
    without re-executing the bridge (see ``advoi.fleet.idempotency``).
    """
    from advoi.fleet.idempotency import normalize_idempotency_key
    from advoi.fleet.trigger import FleetVoiceAction, fleet_trigger_from_voice

    allowed: tuple[FleetVoiceAction, ...] = (
        "wake_firstmate",
        "start_development",
        "run_next_backlog",
        "fleet_stop",
    )
    if body.action not in allowed:
        raise HTTPException(status_code=400, detail=f"Unknown action: {body.action}")

    # Header wins over body (standard Idempotency-Key convention).
    header_key = request.headers.get("Idempotency-Key") or request.headers.get("idempotency-key")
    idem_key = normalize_idempotency_key(header_key) or normalize_idempotency_key(
        body.idempotency_key
    )

    transcript = body.transcript or body.action.replace("_", " ")
    if body.project:
        transcript = f"{transcript} on {body.project}"
    if body.task:
        transcript = f"{transcript} {body.task}"

    # All live fleet writes go through the Guardian-gated voice/API action helper.
    # Free-form low-level bridge invoke is not exposed on this endpoint.
    return await fleet_trigger_from_voice(
        body.action,  # type: ignore[arg-type]
        transcript=transcript,
        confirmed=body.confirmed,
        idempotency_key=idem_key,
    )


class IngestDispatchRequest(BaseModel):
    confirmed: bool = False
    mode: str = "work"


class IngestRerouteRequest(BaseModel):
    project_hint: str | None = None


class IngestTriageRequest(BaseModel):
    project_hint: str | None = None


def _ingestion_lifecycle_error(exc: Exception) -> HTTPException:
    from advoi.ingestion.lifecycle import InvalidTransitionError

    if isinstance(exc, InvalidTransitionError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=500, detail=str(exc))


@app.get("/api/ingestion/summary")
async def ingestion_status() -> dict[str, Any]:
    from advoi.ingestion.pipeline import ingestion_summary

    return ingestion_summary()


@app.get("/api/ingestion/items")
async def ingestion_list(status: str | None = None) -> dict[str, Any]:
    from advoi.ingestion.store import list_items

    items = list_items(status=status)  # type: ignore[arg-type]
    return {"items": [i.to_dict() for i in items], "count": len(items)}


@app.get("/api/ingestion/items/{item_id}")
async def ingestion_get(item_id: str) -> dict[str, Any]:
    from advoi.ingestion.store import get_item

    item = get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Ingestion item not found")
    return item.to_dict()


@app.post("/api/ingestion/upload")
async def ingestion_upload(
    file: UploadFile = File(...),
    project_hint: str | None = Form(None),
    venture_hint: str | None = Form(None),
    paperclip_ticket_id: str | None = Form(None),
) -> dict[str, Any]:
    """Upload only — status stays ``uploaded``; no auto-dispatch (M7 lifecycle)."""
    from advoi.ingestion.pipeline import ingest_upload

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    item = await ingest_upload(
        file.filename or "upload.txt",
        data,
        mime_type=file.content_type,
        project_hint=project_hint,
        venture_hint=venture_hint,
        paperclip_ticket_id=paperclip_ticket_id,
    )
    payload: dict[str, Any] = {"ok": item.status != "failed", "item": item.to_dict()}
    if item.status == "failed":
        payload["error"] = item.error
    return payload


@app.post("/api/ingestion/items/{item_id}/triage")
async def ingestion_triage(
    item_id: str,
    body: IngestTriageRequest | None = None,
) -> dict[str, Any]:
    """Transition ``uploaded`` → ``triaged``."""
    from advoi.ingestion.pipeline import triage_item

    try:
        item = await triage_item(
            item_id,
            project_hint=body.project_hint if body else None,
        )
    except Exception as exc:
        raise _ingestion_lifecycle_error(exc) from exc
    return {"ok": True, "item": item.to_dict()}


@app.post("/api/ingestion/items/{item_id}/needs-review")
async def ingestion_needs_review(item_id: str) -> dict[str, Any]:
    """Transition ``triaged`` → ``needs_review``."""
    from advoi.ingestion.pipeline import mark_needs_review

    try:
        item = await mark_needs_review(item_id)
    except Exception as exc:
        raise _ingestion_lifecycle_error(exc) from exc
    return {"ok": True, "item": item.to_dict()}


@app.post("/api/ingestion/items/{item_id}/approve")
async def ingestion_approve(item_id: str) -> dict[str, Any]:
    """Transition ``needs_review`` → ``approved`` (required before dispatch)."""
    from advoi.ingestion.pipeline import approve_item

    try:
        item = await approve_item(item_id)
    except Exception as exc:
        raise _ingestion_lifecycle_error(exc) from exc
    return {"ok": True, "item": item.to_dict()}


@app.post("/api/ingestion/items/{item_id}/route")
async def ingestion_reroute(
    item_id: str, body: IngestRerouteRequest | None = None
) -> dict[str, Any]:
    from advoi.ingestion.pipeline import reroute_item

    try:
        item = await reroute_item(
            item_id,
            project_hint=body.project_hint if body else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, "item": item.to_dict()}


@app.post("/api/ingestion/items/{item_id}/dispatch-dev")
async def ingestion_dispatch_dev(
    item_id: str,
    body: IngestDispatchRequest | None = None,
) -> dict[str, Any]:
    """Dispatch to FirstMate — only when item status is ``approved``."""
    from advoi.ingestion.pipeline import dispatch_item_dev

    req = body or IngestDispatchRequest()
    result = await dispatch_item_dev(
        item_id,
        confirmed=req.confirmed,
        mode=req.mode,
    )
    if result.get("status") == "not_approved":
        raise HTTPException(status_code=409, detail=result.get("error") or "not approved")
    return result


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
    pending_operator: str | None = None
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
    squads: dict[str, Any] | None = None


class SquadDispatchRequest(BaseModel):
    squad_id: str
    action: str = "manual_dispatch"
    confirmed: bool = True


class VoiceIntentRequest(BaseModel):
    transcript: str
    preview: bool = False


class VoiceOperatorPreview(BaseModel):
    spoken: str
    action: str = "chat"
    agent_id: str | None = None
    agent_name: str | None = None
    frame_id: str | None = None
    pending_operator: str | None = None
    agents_used: list[str] = Field(default_factory=list)
    systems: list[str] = Field(default_factory=list)


class VoiceIntentResponse(BaseModel):
    transcript: str
    action: str
    frame_id: str | None = None
    frame_label: str | None = None
    confirmed: bool | None = None
    preview: FrameRunResponse | None = None
    operator_preview: VoiceOperatorPreview | None = None


@app.get("/api/capabilities")
async def capabilities_catalog() -> dict[str, Any]:
    from advoi.voice.capabilities import build_capabilities_payload

    return build_capabilities_payload()


@app.post("/api/voice/intent", response_model=VoiceIntentResponse)
async def voice_intent(body: VoiceIntentRequest) -> VoiceIntentResponse:
    from advoi.voice.capabilities import classify_operator_intent
    from advoi.voice.respond import _reply_operator_intent

    op = classify_operator_intent(body.transcript)
    if op:
        operator_preview: VoiceOperatorPreview | None = None
        if body.preview:
            reply = await _reply_operator_intent(op, transcript=body.transcript)
            if reply:
                operator_preview = VoiceOperatorPreview(
                    spoken=reply.spoken,
                    action=reply.action,
                    agent_id=reply.agent_id,
                    agent_name=reply.agent_name,
                    frame_id=reply.frame_id,
                    pending_operator=reply.pending_operator,
                    agents_used=reply.agents_used,
                    systems=reply.systems,
                )
        return VoiceIntentResponse(
            transcript=body.transcript,
            action=op,
            frame_id=None,
            frame_label=None,
            confirmed=None,
            preview=None,
            operator_preview=operator_preview,
        )

    action = resolve_voice_action(body.transcript)
    frame_id = action.get("frame_id") if action["action"] == "frame" else None
    confirmed = action.get("confirmed") if action["action"] == "frame" else None
    preview: FrameRunResponse | None = None

    if body.preview and frame_id:
        require_frame_id(str(frame_id))
        result = await run_frame(frame_id, confirmed=bool(confirmed))
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
        pending_operator=reply.pending_operator,
        agents_used=reply.agents_used,
        systems=reply.systems,
    )


@app.post("/api/agents/orchestrate", response_model=OrchestrateResponse)
async def orchestrate_agents(body: OrchestrateRequest) -> OrchestrateResponse:
    frame_ids = body.frame_ids or ["fleet_status", "open_briefs"]
    for fid in frame_ids:
        require_frame_id(fid)
    results = await run_frames_parallel(
        frame_ids,  # type: ignore[arg-type]
        confirmed=body.confirmed,
        refresh=body.refresh,
    )

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
    dispatch_squads: bool = False,
) -> OrchestrateResponse:
    """Run all six specialist frames in parallel."""
    from advoi.squads.orchestrate import run_six_with_platform

    payload = await run_six_with_platform(
        confirmed=confirmed,
        refresh=refresh,
        dispatch_squads=dispatch_squads,
        retain_memory=True,
    )
    rows = [_frame_run_response(r) for r in payload["results"]]
    return OrchestrateResponse(
        results=rows,
        agents_used=payload["agents_used"],
        systems=payload["systems"],
        spoken_summary=payload["spoken_summary"],
        squads=payload.get("squads"),
    )


@app.get("/api/squads")
async def list_squads() -> dict[str, Any]:
    from advoi.squads.registry import squads_summary

    return squads_summary()


@app.post("/api/squads/dispatch")
async def dispatch_squad(body: SquadDispatchRequest) -> dict[str, Any]:
    from advoi.squads.dispatch import dispatch_squad_job

    return await dispatch_squad_job(
        body.squad_id,
        action=body.action,
        confirmed=body.confirmed,
    )


@app.post("/api/squads/dispatch-all")
async def dispatch_all_squads_endpoint(confirmed: bool = True) -> dict[str, Any]:
    from advoi.squads.orchestrate import dispatch_all_squads

    return await dispatch_all_squads(confirmed=confirmed)


@app.get("/api/diagnostics/platform")
async def platform_diagnostics_endpoint() -> dict[str, Any]:
    from advoi.diagnostics.platform import platform_diagnostics

    return await platform_diagnostics()


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
        "operational_store_enabled": os.getenv("ADVOI_OPERATIONAL_STORE_ENABLED", "true").lower()
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
    fleet_ops = [
        {
            "action": action,
            "requires_confirmation": fleet_action_needs_confirmation(action),
        }
        for action in (
            "wake_firstmate",
            "start_development",
            "run_next_backlog",
            "fleet_stop",
        )
    ]
    return {
        "ok": True,
        "confirmation_enabled": global_confirmation_enabled(),
        "frames": frames,
        "high_risk_frames": [row["frame_id"] for row in frames if row["requires_confirmation"]],
        "fleet_actions": fleet_ops,
        "high_risk_fleet_actions": high_risk_fleet_actions(),
    }


@app.post("/api/frames/{frame_id}/run", response_model=FrameRunResponse)
async def run_decision_frame(
    frame_id: str,
    body: FrameRunRequest | None = None,
    refresh: bool = False,
) -> FrameRunResponse:
    # Explicit registry check so unregistered ids never reach runners as 500/404.
    require_frame_id(frame_id)
    req = body or FrameRunRequest()
    result = await run_frame(
        frame_id,
        confirmed=req.confirmed,
        refresh=refresh or req.refresh,
    )
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
            "OPENROUTER_API_KEY or OPENAI_API_KEY is required; "
            "advoi-voice exits at startup without it."
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

    run_six_ms: float | None = None
    try:
        started = time.perf_counter()
        bundle = await run_all_specialist_frames(confirmed=True, refresh=True)
        run_six_ms = round((time.perf_counter() - started) * 1000, 1)
        timings_ms["run_six_ms"] = run_six_ms
        timings_ms["run_six_frames"] = len(bundle.results)
    except Exception as exc:
        timings_ms["run_six_ms"] = None
        timings_ms["run_six_error"] = str(exc)

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
        "sla_scope": (
            "API intent + frame preview only; full mic-STT-TTS round trip not measured here"
        ),
        "frame_id": frame_latency.get("frame_id", "fleet_status"),
        "frame_status": frame_latency.get("frame_status"),
        "intent_frame_id": intent_latency.get("intent_frame_id"),
        "respond_chars": respond_latency.get("respond_chars"),
    }
