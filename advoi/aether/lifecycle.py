"""Aether lifecycle — gate-aligned active venture and portfolio health."""

from __future__ import annotations

import os
from typing import Any

from advoi.aether.gate import load_gate_snapshot
from advoi.aether.models import Venture
from advoi.aether.portfolio import VENTURES, venture_for_frame, venture_to_dict
from advoi.portfolio.ecr import resolve_execution_target


def resolve_active_venture(*, gate_active_slug: str | None = None) -> Venture | None:
    """Map gate active slug to a portfolio venture when possible."""
    slug = (gate_active_slug or "").strip().lower()
    if not slug:
        return None
    for venture in VENTURES:
        if venture.id.lower() == slug:
            return venture
        if slug in {t.lower() for t in venture.tags}:
            return venture
        if slug in venture.id.lower():
            return venture
    return None


def lifecycle_status() -> dict[str, Any]:
    """Portfolio + gate alignment for API, CLI, and voice context."""
    gate = load_gate_snapshot()
    active = resolve_active_venture(gate_active_slug=gate.active_slug)
    frame_coverage: dict[str, str | None] = {}
    for venture in VENTURES:
        for frame_id in venture.primary_frames:
            frame_coverage.setdefault(frame_id, venture.id)

    unmapped_frames = [
        frame_id
        for frame_id in (
            "fleet_status",
            "open_briefs",
            "queue_deep_review",
            "systems_pulse",
            "memory_health",
            "guardian_status",
        )
        if frame_id not in frame_coverage
    ]

    execution_context = resolve_execution_target(gate_active_slug=gate.active_slug)

    return {
        "gate": gate.to_dict(),
        "active_venture": venture_to_dict(active) if active else None,
        "active_venture_resolved": active is not None,
        "execution_context": execution_context,
        "portfolio_total": len(VENTURES),
        "frame_coverage": frame_coverage,
        "unmapped_frames": unmapped_frames,
        "letta_enabled": os.getenv("LETTA_ENABLED", "false").lower() in {"1", "true", "yes"},
        "operational_bridge": "letta" if os.getenv("LETTA_ENABLED", "false").lower() in {"1", "true", "yes"} else "operational_store",
        "portfolio_path": os.getenv("AETHER_PORTFOLIO_PATH", "data/aether/portfolio.json"),
    }


def venture_is_active_for_frame(frame_id: str) -> bool:
    gate = load_gate_snapshot()
    active = resolve_active_venture(gate_active_slug=gate.active_slug)
    if not active:
        return False
    routed = venture_for_frame(frame_id)
    return routed is not None and routed.id == active.id