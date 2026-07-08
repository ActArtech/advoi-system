"""Shared specialist agent daemon configuration."""

from __future__ import annotations

import os

AGENT_FRAMES: dict[str, str] = {
    "fleet-scout": "fleet_status",
    "brief-curator": "open_briefs",
    "review-queue": "queue_deep_review",
}

INTERVAL_SECS = int(os.getenv("ADVOI_AGENT_INTERVAL_SECS", "45"))

# Stagger daemon ticks so fleet/briefs/review do not hammer disk/DB at once.
TICK_STAGGER_SECS: dict[str, int] = {
    "fleet-scout": 0,
    "brief-curator": 8,
    "review-queue": 16,
}