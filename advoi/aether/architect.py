"""Aether architect — portfolio context for prompts and post-frame memory."""

from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

from advoi.aether.gate import load_gate_snapshot
from advoi.aether.models import PortfolioContext
from advoi.aether.portfolio import portfolio_summary, venture_for_frame, venture_to_dict
from advoi.aether.router import enrich_frame_context
from advoi.memory import MemoryRouter
from advoi.memory.write_targets import MemoryEventType

if TYPE_CHECKING:
    from advoi.routing.frame_runner import FrameResult

_LOGGER = logging.getLogger(__name__)


def build_portfolio_context() -> PortfolioContext:
    portfolio = portfolio_summary()
    gate = load_gate_snapshot()
    routes: dict[str, list[str]] = {}
    for v in portfolio["ventures"]:
        for fid in v.get("primary_frames", []):
            routes.setdefault(fid, []).append(v["id"])
    return PortfolioContext(
        ventures=portfolio["ventures"],
        active_count=int(portfolio.get("active_count", 0)),
        gate=gate,
        frame_routes=routes,
    )


async def recall_portfolio_context(*, query: str = "portfolio executive context") -> str:
    """Strategic + operational recall for voice and frame prompts."""
    router = MemoryRouter()
    recall = await router.recall(session_id="aether-portfolio", query=query)
    chunks: list[str] = []
    ctx = build_portfolio_context()
    block = ctx.prompt_block()
    if block:
        chunks.append(block)
    for item in recall.strategic + recall.operational:
        text = item.get("text") or item.get("content") or item.get("summary")
        if text:
            chunks.append(str(text))
    return "\n".join(chunks[:8])


async def post_frame_aether(result: FrameResult) -> None:
    """Enrich frame detail and retain operational memory after a successful run."""
    result.detail = enrich_frame_context(result.frame_id, result.detail)

    if result.status not in {"ok", "confirmation_required"}:
        return

    venture = venture_for_frame(result.frame_id)
    payload: dict[str, Any] = {
        "summary": result.spoken_summary[:500],
        "frame_id": result.frame_id,
        "agent_id": result.agent_id,
        "status": result.status,
        "venture_id": venture.id if venture else None,
    }

    router = MemoryRouter()
    try:
        await router.retain(MemoryEventType.SQUAD_LESSON, payload, session_id="aether-ops")
    except Exception as exc:
        _LOGGER.debug("aether squad_lesson retain skip: %s", exc)

    if venture and result.status == "ok":
        belief = {
            "summary": f"{venture.name}: {result.frame_id} ran OK.",
            "venture_id": venture.id,
            "frame_id": result.frame_id,
        }
        try:
            await router.retain(MemoryEventType.VENTURE_BELIEF_UPDATE, belief)
        except Exception as exc:
            _LOGGER.debug("aether belief retain skip: %s", exc)


def venture_context_for_frame(frame_id: str) -> dict[str, Any] | None:
    venture = venture_for_frame(frame_id)
    return venture_to_dict(venture) if venture else None