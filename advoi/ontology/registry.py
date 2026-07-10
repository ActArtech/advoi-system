"""Ontology registry — vocabulary enforcement for frames, agents, and ventures.

Single read-only source of truth for valid identifiers used across voice,
API, routing, and memory write paths. Membership helpers live here;
structured raise-on-unknown validators are in ``advoi.ontology.validate``
(HTTP 422 mapping is applied at the API / frame-runner boundary).

Sources:
- frame_id  → advoi.decision.frames.FRAMES
- agent_id  → advoi.routing.agents.AGENTS
- venture_id → data/aether/portfolio.json (builtin fallback via aether.portfolio)
"""

from __future__ import annotations

from advoi.aether import portfolio as portfolio_mod
from advoi.decision.frames import FRAMES, FRAMES_BY_ID
from advoi.routing.agents import AGENTS


def is_valid_frame_id(frame_id: str) -> bool:
    """Return True if frame_id is in the decision frame catalog."""
    return frame_id in FRAMES_BY_ID


def is_valid_agent_id(agent_id: str) -> bool:
    """Return True if agent_id is a registered specialist agent."""
    return agent_id in AGENTS


def is_valid_venture_id(venture_id: str) -> bool:
    """Return True if venture_id is in the loaded portfolio (or builtin fallback)."""
    # Access via module so reload_portfolio() reassignment is visible.
    return venture_id in portfolio_mod.VENTURES_BY_ID


def list_frames() -> list[str]:
    """Return ordered frame ids from the decision catalog."""
    return [frame.id for frame in FRAMES]


def list_agents() -> list[str]:
    """Return registered specialist agent ids (dict insertion order)."""
    return list(AGENTS.keys())


def list_ventures() -> list[str]:
    """Return venture ids from portfolio config (or builtin fallback)."""
    return list(portfolio_mod.VENTURES_BY_ID.keys())
