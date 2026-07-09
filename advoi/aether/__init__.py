"""Portfolio manager + venture architect."""

from advoi.aether.architect import build_portfolio_context, post_frame_aether, recall_portfolio_context
from advoi.aether.gate import load_gate_snapshot
from advoi.aether.lifecycle import lifecycle_status, resolve_active_venture
from advoi.aether.portfolio import portfolio_summary, venture_for_frame
from advoi.aether.router import enrich_frame_context, route_summary
from advoi.aether.service import AetherService, get_aether_service

__all__ = [
    "AetherService",
    "build_portfolio_context",
    "enrich_frame_context",
    "get_aether_service",
    "lifecycle_status",
    "load_gate_snapshot",
    "resolve_active_venture",
    "portfolio_summary",
    "post_frame_aether",
    "recall_portfolio_context",
    "route_summary",
    "venture_for_frame",
]