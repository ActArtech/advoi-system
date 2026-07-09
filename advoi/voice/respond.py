"""Warm spoken replies for client-side voice loop."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

import httpx

from advoi.cache.agent_cache import agents_status_summary, read_all_agent_caches
from advoi.copy_style import plain_copy
from advoi.llm.openrouter import resolve_llm_credentials
from advoi.memory import MemoryRouter
from advoi.routing.agents import AGENTS
from advoi.routing.frame_runner import run_frame
from advoi.routing.intent import resolve_voice_action
from advoi.routing.orchestrator import systems_for_frame
from advoi.voice.memory_hooks import retain_turn
from advoi.voice.capabilities import (
    classify_operator_intent,
    spoken_capabilities_summary,
    spoken_firstmate_access,
    spoken_github_access,
)
from advoi.voice.prompts import LOCAL_VOICE_SESSION, build_warm_system_instruction
from advoi.routing.agent_control import (
    restart_agent_daemons,
    spoken_restart_agents,
    spoken_stop_agents,
    stop_agent_daemons,
)
from advoi.routing.orchestrator import run_frames_parallel, synthesize_systems_pulse

_LOGGER = logging.getLogger(__name__)


@dataclass
class VoiceReply:
    spoken: str
    action: str = "chat"
    agent_id: str | None = None
    agent_name: str | None = None
    frame_id: str | None = None
    agents_used: list[str] = field(default_factory=list)
    systems: list[str] = field(default_factory=list)


def _stop_agents_needs_confirm(transcript: str) -> bool:
    if os.getenv("ADVOI_CONFIRMATION_REQUIRED", "true").lower() not in {
        "1",
        "true",
        "yes",
    }:
        return False
    lowered = transcript.lower()
    return not any(w in lowered for w in ("confirm", "confirmed", "yes go ahead"))


def _agent_roster_context() -> str:
    lines = ["Specialist agents you can route to by voice:"]
    for agent in AGENTS.values():
        lines.append(f"- {agent.name} ({agent.id}): {agent.role}")
    summary = agents_status_summary()
    lines.append(
        f"Agent cache: {summary.get('ready', 0)}/{summary.get('total', 0)} warm."
    )
    try:
        caches = read_all_agent_caches()
    except Exception:
        caches = {}
    for agent_id, payload in caches.items():
        agent = AGENTS.get(agent_id)
        if not agent:
            continue
        spoken = str(payload.get("spoken_summary", ""))[:140]
        if spoken:
            lines.append(f"  Latest {agent.name}: {spoken}")
    lines.append('For a full cross-system read, suggest "systems pulse" or "run all agents".')
    lines.append('For capabilities, user can say "what can you do".')
    return "\n".join(lines)


async def _reply_operator_intent(intent: str) -> VoiceReply | None:
    if intent == "capabilities":
        spoken = spoken_capabilities_summary()
        return VoiceReply(
            spoken=spoken,
            action="capabilities",
            agent_id="advoi-core",
            agent_name="ADVoi Core",
            systems=["operators"],
        )
    if intent == "firstmate_info":
        return VoiceReply(
            spoken=spoken_firstmate_access(),
            action="firstmate_info",
            agent_id="advoi-core",
            agent_name="ADVoi Core",
            systems=["firstmate"],
        )
    if intent == "github_info":
        return VoiceReply(
            spoken=spoken_github_access(),
            action="github_info",
            agent_id="advoi-core",
            agent_name="ADVoi Core",
            systems=["github", "firstmate"],
        )
    if intent == "stop_agents":
        result = await stop_agent_daemons(docker=False)
        return VoiceReply(
            spoken=spoken_stop_agents(result),
            action="stop_agents",
            agent_id="advoi-core",
            agent_name="ADVoi Core",
            systems=["redis", "agents"],
        )
    if intent == "restart_agents":
        result = await restart_agent_daemons(docker=False)
        return VoiceReply(
            spoken=spoken_restart_agents(result),
            action="restart_agents",
            agent_id="advoi-core",
            agent_name="ADVoi Core",
            systems=["redis", "agents"],
        )
    if intent == "run_all":
        from advoi.decision.frames import FRAMES

        frame_ids = [f.id for f in FRAMES if f.id != "systems_pulse"]
        parallel = await run_frames_parallel(
            frame_ids,  # type: ignore[arg-type]
            confirmed=True,
            refresh=True,
        )
        fleet = next((r for r in parallel if r.frame_id == "fleet_status"), None)
        briefs = next((r for r in parallel if r.frame_id == "open_briefs"), None)
        if fleet and briefs:
            spoken, _ = synthesize_systems_pulse(fleet, briefs)
        else:
            spoken = "Ran all specialist agents. Say systems pulse for a merged summary."
        agents_used = list({r.agent_id for r in parallel})
        return VoiceReply(
            spoken=plain_copy(spoken),
            action="run_all",
            agent_id="systems-pulse",
            agent_name="Systems Pulse",
            frame_id="systems_pulse",
            agents_used=agents_used,
            systems=["api", "firstmate", "memory"],
        )
    return None


def _reply_from_frame(result) -> VoiceReply:
    agent = AGENTS.get(result.agent_id)
    return VoiceReply(
        spoken=plain_copy(result.spoken_summary),
        action="frame",
        agent_id=result.agent_id,
        agent_name=agent.name if agent else None,
        frame_id=result.frame_id,
        agents_used=list(result.detail.get("agents_used") or [result.agent_id]),
        systems=systems_for_frame(result.frame_id),
    )


async def _memory_context(*, session_id: str, query: str) -> str:
    from advoi.aether.architect import recall_portfolio_context

    router = MemoryRouter()
    recall = await router.recall(session_id=session_id, query=query)
    chunks: list[str] = []
    try:
        aether_block = await recall_portfolio_context(query=query)
        if aether_block:
            chunks.append(aether_block)
    except Exception as exc:
        _LOGGER.debug("aether context skip: %s", exc)
    for item in recall.strategic + recall.operational + recall.ephemeral:
        text = item.get("text") or item.get("content") or item.get("summary")
        if text:
            chunks.append(str(text))
    return "\n".join(chunks[:8])


async def warm_spoken_reply(
    transcript: str,
    *,
    recent_phrases: list[str] | None = None,
    session_id: str = LOCAL_VOICE_SESSION,
    temperature: float = 0.8,
) -> VoiceReply:
    text = (transcript or "").strip()
    if not text:
        return VoiceReply(
            spoken="I did not catch that. Try again when you are ready.",
            action="chat",
        )

    op = classify_operator_intent(text)
    if op == "stop_agents" and _stop_agents_needs_confirm(text):
        return VoiceReply(
            spoken="To pause background agent daemons, say stop agents confirm.",
            action="confirmation_required",
            agent_id="advoi-core",
            agent_name="ADVoi Core",
            systems=["agents"],
        )
    if op:
        reply = await _reply_operator_intent(op)
        if reply:
            try:
                await retain_turn(session_id=session_id, role="user", text=text)
                await retain_turn(session_id=session_id, role="assistant", text=reply.spoken)
            except Exception as exc:
                _LOGGER.debug("voice operator retain skip: %s", exc)
            return reply

    action = resolve_voice_action(text)
    if action["action"] == "frame":
        result = await run_frame(
            action["frame_id"],
            confirmed=action["confirmed"],
        )
        reply = _reply_from_frame(result)
        try:
            await retain_turn(session_id=session_id, role="user", text=text)
            await retain_turn(session_id=session_id, role="assistant", text=reply.spoken)
        except Exception as exc:
            _LOGGER.debug("voice-local frame retain skip: %s", exc)
        return reply

    memory_context = ""
    try:
        memory_context = await _memory_context(session_id=session_id, query=text)
    except Exception as exc:
        _LOGGER.debug("voice-local recall skip: %s", exc)

    creds = resolve_llm_credentials()
    base_url = (creds.base_url or "https://api.openai.com/v1").rstrip("/")

    messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": build_warm_system_instruction(memory_context=memory_context),
        },
        {"role": "system", "content": _agent_roster_context()},
    ]
    if recent_phrases:
        mirror = ", ".join(p for p in recent_phrases if p.strip())[:120]
        if mirror:
            messages.append(
                {
                    "role": "system",
                    "content": f"Mirror one or two of these user phrases lightly: {mirror}",
                }
            )
    messages.append({"role": "user", "content": text})

    headers = {"Authorization": f"Bearer {creds.api_key}", "Content-Type": "application/json"}
    if creds.provider == "openrouter":
        headers["HTTP-Referer"] = "https://advoi.keyteller.com"
        headers["X-Title"] = "ADVoi local voice loop"

    async with httpx.AsyncClient(timeout=45.0) as client:
        resp = await client.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json={
                "model": creds.llm_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": 220,
            },
        )
        resp.raise_for_status()
        raw = resp.json()["choices"][0]["message"]["content"]

    spoken = plain_copy(str(raw).strip())

    try:
        await retain_turn(session_id=session_id, role="user", text=text)
        await retain_turn(session_id=session_id, role="assistant", text=spoken)
    except Exception as exc:
        _LOGGER.debug("voice-local retain skip: %s", exc)

    return VoiceReply(
        spoken=spoken,
        action="chat",
        agent_id="advoi-core",
        agent_name="ADVoi Core",
        systems=["llm", "memory"],
    )