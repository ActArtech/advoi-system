"""Aether architect — portfolio context for prompts and post-frame memory."""

from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

from advoi.aether.gate import load_gate_snapshot
from advoi.aether.models import PortfolioContext
from advoi.aether.portfolio import portfolio_summary, venture_for_frame, venture_to_dict
from advoi.aether.router import enrich_frame_context
from advoi.memory import MemoryRouter
from advoi.memory.write_targets import EVENT_WRITE_MAP, MemoryEventType, targets_for

if TYPE_CHECKING:
    from advoi.routing.frame_runner import FrameResult

_LOGGER = logging.getLogger(__name__)

# ADR-026: post-frame hook may only retain types present in EVENT_WRITE_MAP.
# Operational lesson after every successful/confirm frame run.
POST_FRAME_OPERATIONAL_EVENT = MemoryEventType.SQUAD_LESSON
# Strategic belief when a venture is mapped and the frame completed ok.
# Payload is a short "ran OK" line — never queue dumps into strategic store.
POST_FRAME_STRATEGIC_EVENT = MemoryEventType.VENTURE_BELIEF_UPDATE

# Closed set of event types the hook is allowed to emit. Keep in sync with
# retain_events_for_frame() and EVENT_WRITE_MAP (guarded below + T0).
POST_FRAME_ALLOWED_EVENTS: frozenset[MemoryEventType] = frozenset(
    {
        POST_FRAME_OPERATIONAL_EVENT,
        POST_FRAME_STRATEGIC_EVENT,
    }
)

# Frames whose tick content is operational-only (no strategic retain).
# fleet_status / fleet-scout: SQUAD_LESSON only (AGENTS.md).
_OPERATIONAL_ONLY_FRAMES: frozenset[str] = frozenset({"fleet_status"})


def _assert_events_on_allowlist(events: tuple[MemoryEventType, ...]) -> None:
    """Raise if any event is outside write_targets or the hook allowlist."""
    for event in events:
        if event not in POST_FRAME_ALLOWED_EVENTS:
            raise ValueError(
                f"post_frame_aether event {event.value!r} not in POST_FRAME_ALLOWED_EVENTS"
            )
        if event not in EVENT_WRITE_MAP:
            raise ValueError(
                f"post_frame_aether event {event.value!r} missing from EVENT_WRITE_MAP"
            )
        if not targets_for(event):
            raise ValueError(f"post_frame_aether event {event.value!r} has empty write targets")


# Import-time alignment check: hook types must always be in write_targets.
_assert_events_on_allowlist(tuple(POST_FRAME_ALLOWED_EVENTS))


def retain_events_for_frame(
    frame_id: str,
    status: str,
    *,
    has_venture: bool,
) -> tuple[MemoryEventType, ...]:
    """Return MemoryEventTypes that post_frame_aether will retain for this run.

    All returned types are members of EVENT_WRITE_MAP (ADR-026 allowlist).
    """
    if status not in {"ok", "confirmation_required"}:
        return ()

    events: list[MemoryEventType] = [POST_FRAME_OPERATIONAL_EVENT]
    if (
        has_venture
        and status == "ok"
        and frame_id not in _OPERATIONAL_ONLY_FRAMES
    ):
        events.append(POST_FRAME_STRATEGIC_EVENT)

    out = tuple(events)
    _assert_events_on_allowlist(out)
    return out


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
    """Enrich frame detail and retain operational memory after a successful run.

    Retain types are chosen via ``retain_events_for_frame`` and must stay on the
    ADR-026 ``EVENT_WRITE_MAP`` allowlist (see ``POST_FRAME_ALLOWED_EVENTS``).

    Call sites use literal ``MemoryEventType.*`` arguments so static retain-audit
    guards can verify production retains never free-form event strings.
    """
    result.detail = enrich_frame_context(result.frame_id, result.detail)

    if result.status not in {"ok", "confirmation_required"}:
        result.detail["aether_retain_events"] = []
        return

    venture = venture_for_frame(result.frame_id)
    events = retain_events_for_frame(
        result.frame_id,
        result.status,
        has_venture=venture is not None,
    )
    # Surface chosen types for T0 / diagnostics (values only).
    result.detail["aether_retain_events"] = [e.value for e in events]

    if not events:
        return

    payload: dict[str, Any] = {
        "summary": result.spoken_summary[:500],
        "frame_id": result.frame_id,
        "agent_id": result.agent_id,
        "status": result.status,
        "venture_id": venture.id if venture else None,
    }

    router = MemoryRouter()
    want_operational = POST_FRAME_OPERATIONAL_EVENT in events
    want_strategic = POST_FRAME_STRATEGIC_EVENT in events

    if want_operational:
        try:
            await router.retain(
                MemoryEventType.SQUAD_LESSON, payload, session_id="aether-ops"
            )
        except Exception as exc:
            _LOGGER.debug("aether squad_lesson retain skip: %s", exc)

    if want_strategic and venture is not None:
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
