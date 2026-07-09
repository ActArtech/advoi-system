"""Aether service facade — single entry for API and voice layers."""

from __future__ import annotations

from typing import Any

from advoi.aether.architect import build_portfolio_context, recall_portfolio_context
from advoi.aether.gate import load_gate_snapshot
from advoi.aether.portfolio import portfolio_summary, reload_portfolio, venture_for_frame, venture_to_dict
from advoi.aether.lifecycle import lifecycle_status
from advoi.aether.router import route_summary


class AetherService:
    """Portfolio manager + venture architect (in-process)."""

    async def portfolio(self) -> dict[str, Any]:
        ctx = build_portfolio_context()
        return {
            "portfolio": portfolio_summary(),
            "gate": ctx.gate.to_dict() if ctx.gate else None,
            "frame_routes": ctx.frame_routes,
        }

    async def gate(self) -> dict[str, Any]:
        snap = load_gate_snapshot()
        return snap.to_dict()

    def routes(self) -> dict[str, Any]:
        return route_summary()

    async def venture(self, venture_id: str) -> dict[str, Any] | None:
        from advoi.aether.portfolio import VENTURES_BY_ID

        v = VENTURES_BY_ID.get(venture_id)  # type: ignore[arg-type]
        if not v:
            return None
        out = venture_to_dict(v)
        out["primary_frame_ids"] = list(v.primary_frames)
        return out

    async def context_for_voice(self, *, query: str) -> str:
        return await recall_portfolio_context(query=query)

    def reload(self) -> dict[str, Any]:
        count = reload_portfolio()
        return {"reloaded": True, "venture_count": count}

    def status(self) -> dict[str, Any]:
        return lifecycle_status()


def get_aether_service() -> AetherService:
    return AetherService()