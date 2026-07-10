"""Specialist agent registry — one agent per decision frame.

Six agents (A–F) match FRAMES in advoi/decision/frames.py.
Architecture docs: docs/architecture/01-system-overview.md, 03-multi-agent.md.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SpecialistAgent:
    id: str
    name: str
    role: str
    speaks_first: str


AGENTS: dict[str, SpecialistAgent] = {
    "fleet-scout": SpecialistAgent(
        id="fleet-scout",
        name="Fleet Scout",
        role="Read-only FirstMate / Hermes fleet status",
        speaks_first="Checking the fleet bridge now.",
    ),
    "brief-curator": SpecialistAgent(
        id="brief-curator",
        name="Brief Curator",
        role="Surface open decision briefs from memory and backlog",
        speaks_first="Pulling open briefs from portfolio memory.",
    ),
    "review-queue": SpecialistAgent(
        id="review-queue",
        name="Review Queue",
        role="Queue async deep review for desktop follow-up, not live execution",
        speaks_first="I can queue a deep review. I'll need your confirmation first.",
    ),
    "systems-pulse": SpecialistAgent(
        id="systems-pulse",
        name="Systems Pulse",
        role="Orchestrate fleet, briefs, and agent cache in one parallel pass",
        speaks_first="Running a systems pulse across fleet and memory now.",
    ),
    "memory-scout": SpecialistAgent(
        id="memory-scout",
        name="Memory Scout",
        role="Probe Hindsight bridge, Redis, Postgres, and operational store health",
        speaks_first="Checking the memory stack now.",
    ),
    "guardian-sentinel": SpecialistAgent(
        id="guardian-sentinel",
        name="Guardian Sentinel",
        role="Surface confirmation policy and recent guardian events",
        speaks_first="Reviewing guardian and safety posture.",
    ),
}
