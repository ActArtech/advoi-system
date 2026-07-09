"""System graph for React Flow — agents, frames, ventures, squads, subsystems."""

from __future__ import annotations

from typing import Any

from advoi.aether.portfolio import VENTURES
from advoi.cache.agent_cache import agents_status_summary
from advoi.decision.frames import FRAMES
from advoi.routing.agents import AGENTS
from advoi.squads.registry import SQUADS, squad_for_agent


def _node(
    nid: str,
    *,
    label: str,
    ntype: str,
    status: str = "unknown",
    meta: dict[str, Any] | None = None,
    x: float = 0,
    y: float = 0,
) -> dict[str, Any]:
    return {
        "id": nid,
        "type": "systemNode",
        "position": {"x": x, "y": y},
        "data": {
            "label": label,
            "nodeType": ntype,
            "status": status,
            "meta": meta or {},
        },
    }


def _edge(source: str, target: str, label: str = "") -> dict[str, Any]:
    eid = f"{source}->{target}"
    if label:
        eid = f"{source}->{target}:{label}"
    return {"id": eid, "source": source, "target": target, "label": label}


async def build_system_graph(*, include_health: bool = True) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    cache_summary = agents_status_summary() if include_health else {"agents": []}
    cached_ids = {
        a["id"] for a in cache_summary.get("agents", []) if a.get("cached")
    }

    nodes.append(_node("advoi-api", label="ADVoi API", ntype="hub", status="ok", x=400, y=40))
    nodes.append(_node("voice-pwa", label="Voice PWA", ntype="client", status="ok", x=120, y=40))
    nodes.append(_node("livekit", label="LiveKit", ntype="subsystem", status="ok", x=680, y=40))
    edges.extend([
        _edge("voice-pwa", "advoi-api", "HTTP"),
        _edge("advoi-api", "livekit", "tokens"),
    ])

    # Ventures row
    for i, venture in enumerate(VENTURES):
        nodes.append(
            _node(
                f"venture:{venture.id}",
                label=venture.name,
                ntype="venture",
                status=venture.status,
                meta={"squads": list(venture.squads)},
                x=80 + i * 220,
                y=160,
            )
        )
        edges.append(_edge(f"venture:{venture.id}", "advoi-api", "portfolio"))

    # Agents + frames (two columns)
    for i, frame in enumerate(FRAMES):
        agent = AGENTS[frame.agent_id]
        row_y = 280 + i * 72
        agent_status = "warm" if frame.agent_id in cached_ids else "idle"
        nodes.append(
            _node(
                f"agent:{frame.agent_id}",
                label=agent.name,
                ntype="agent",
                status=agent_status,
                meta={"role": agent.role},
                x=80,
                y=row_y,
            )
        )
        nodes.append(
            _node(
                f"frame:{frame.id}",
                label=frame.label.replace("Option ", ""),
                ntype="frame",
                status="ok",
                meta={
                    "requires_confirmation": frame.requires_confirmation,
                    "voice_prompt": frame.voice_prompt,
                },
                x=320,
                y=row_y,
            )
        )
        edges.extend([
            _edge("advoi-api", f"agent:{frame.agent_id}", "tick"),
            _edge(f"agent:{frame.agent_id}", f"frame:{frame.id}", "owns"),
        ])
        squad = squad_for_agent(frame.agent_id)
        if squad:
            edges.append(_edge(f"agent:{frame.agent_id}", f"squad:{squad.id}", "member"))

    # Squads row
    for i, squad in enumerate(SQUADS):
        nodes.append(
            _node(
                f"squad:{squad.id}",
                label=squad.name,
                ntype="squad",
                status="ready",
                meta={"channel": squad.channel, "venture_id": squad.venture_id},
                x=560 + (i % 2) * 180,
                y=280 + (i // 2) * 90,
            )
        )
        edges.append(
            _edge(f"squad:{squad.id}", f"venture:{squad.venture_id}", "venture")
        )

    subsystems = [
        ("subsystem:memory", "Memory Stack", 80, 780),
        ("subsystem:guardian", "Guardian", 280, 780),
        ("subsystem:aether", "Aether", 480, 780),
    ]
    for sid, label, x, y in subsystems:
        nodes.append(_node(sid, label=label, ntype="subsystem", status="ok", x=x, y=y))
        edges.append(_edge("advoi-api", sid, "probe"))

    return {
        "nodes": nodes,
        "edges": edges,
        "meta": {
            "agents_total": len(AGENTS),
            "frames_total": len(FRAMES),
            "ventures_total": len(VENTURES),
            "squads_total": len(SQUADS),
            "agents_ready": len(cached_ids),
        },
    }