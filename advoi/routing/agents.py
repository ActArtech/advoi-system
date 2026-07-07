"""Specialist agent registry — one agent per decision frame."""

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
        role="Queue async deep review — desktop follow-up, not live execution",
        speaks_first="I can queue a deep review. I'll need your confirmation first.",
    ),
}