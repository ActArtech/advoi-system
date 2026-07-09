"""Shared specialist agent daemon configuration."""

from __future__ import annotations

import os

AGENT_FRAMES: dict[str, str] = {
    "fleet-scout": "fleet_status",
    "brief-curator": "open_briefs",
    "review-queue": "queue_deep_review",
    "systems-pulse": "systems_pulse",
    "memory-scout": "memory_health",
    "guardian-sentinel": "guardian_status",
}

INTERVAL_SECS = int(os.getenv("ADVOI_AGENT_INTERVAL_SECS", "45"))

# Stagger daemon ticks so specialists do not hammer disk/DB at once.
TICK_STAGGER_SECS: dict[str, int] = {
    "fleet-scout": 0,
    "brief-curator": 8,
    "review-queue": 16,
    "systems-pulse": 24,
    "memory-scout": 32,
    "guardian-sentinel": 40,
}