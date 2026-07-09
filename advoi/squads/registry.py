"""Squad registry — execution crews mapped to specialist agents."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Squad:
    id: str
    name: str
    channel: str
    agent_ids: tuple[str, ...]
    venture_id: str
    dispatch_target: str


SQUADS: tuple[Squad, ...] = (
    Squad(
        id="fleet-squad",
        name="Fleet Squad",
        channel="firstmate",
        agent_ids=("fleet-scout",),
        venture_id="firstmate-fleet",
        dispatch_target="fleet_status",
    ),
    Squad(
        id="briefs-squad",
        name="Briefs Squad",
        channel="hermes",
        agent_ids=("brief-curator",),
        venture_id="hermes-beacon",
        dispatch_target="open_briefs",
    ),
    Squad(
        id="review-squad",
        name="Review Squad",
        channel="advoi",
        agent_ids=("review-queue",),
        venture_id="advoi-system",
        dispatch_target="queue_deep_review",
    ),
    Squad(
        id="platform-squad",
        name="Platform Squad",
        channel="advoi",
        agent_ids=("systems-pulse", "memory-scout", "guardian-sentinel"),
        venture_id="advoi-system",
        dispatch_target="systems_pulse",
    ),
)

SQUADS_BY_ID: dict[str, Squad] = {s.id: s for s in SQUADS}

AGENT_SQUAD_MAP: dict[str, str] = {}
for squad in SQUADS:
    for agent_id in squad.agent_ids:
        AGENT_SQUAD_MAP[agent_id] = squad.id


def squad_for_agent(agent_id: str) -> Squad | None:
    sid = AGENT_SQUAD_MAP.get(agent_id)
    return SQUADS_BY_ID.get(sid) if sid else None


def squads_summary() -> dict:
    return {
        "squads": [
            {
                "id": s.id,
                "name": s.name,
                "channel": s.channel,
                "agent_ids": list(s.agent_ids),
                "venture_id": s.venture_id,
                "dispatch_target": s.dispatch_target,
            }
            for s in SQUADS
        ],
        "total": len(SQUADS),
    }