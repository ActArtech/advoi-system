"""Aether venture routing — attach portfolio context to frame runs."""

from __future__ import annotations

from typing import Any

from advoi.aether.gate import load_gate_snapshot
from advoi.aether.lifecycle import resolve_active_venture, venture_is_active_for_frame
from advoi.aether.portfolio import venture_for_frame, portfolio_summary


def enrich_frame_context(frame_id: str, detail: dict[str, Any] | None = None) -> dict[str, Any]:
    """Add venture routing metadata to a frame result detail dict."""
    out = dict(detail or {})
    venture = venture_for_frame(frame_id)
    gate = load_gate_snapshot()
    if venture:
        out["venture_id"] = venture.id
        out["venture_name"] = venture.name
        out["squads"] = list(venture.squads)
        if venture.bets:
            out["active_bet"] = {
                "id": venture.bets[0].id,
                "name": venture.bets[0].name,
                "status": venture.bets[0].status,
            }
    out["aether_routed"] = venture is not None
    out["gate_verdict"] = gate.verdict if gate.found else None
    out["gate_active_slug"] = gate.active_slug
    active = resolve_active_venture(gate_active_slug=gate.active_slug)
    if active:
        out["portfolio_active_venture"] = active.id
    out["is_gate_active_venture"] = venture_is_active_for_frame(frame_id)
    return out


def route_summary() -> dict[str, Any]:
    """Portfolio + frame-to-venture map for API and dashboard."""
    portfolio = portfolio_summary()
    routes: dict[str, list[str]] = {}
    for v in portfolio["ventures"]:
        for fid in v.get("primary_frames", []):
            routes.setdefault(fid, []).append(v["id"])
    return {
        "portfolio": portfolio,
        "frame_routes": routes,
    }