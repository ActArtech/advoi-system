"""Aether post-frame memory hook tests (ADR-026 retain types)."""

import os

import pytest

os.environ.setdefault("ADVOI_FRAME_MOCK", "true")
os.environ.setdefault("OPENAI_API_KEY", "sk-test")
os.environ.setdefault("LIVEKIT_URL", "wss://example.livekit.cloud")
os.environ.setdefault("LIVEKIT_API_KEY", "testkey")
os.environ.setdefault("LIVEKIT_API_SECRET", "testsecret")

from advoi.aether.architect import (  # noqa: E402
    POST_FRAME_ALLOWED_EVENTS,
    POST_FRAME_OPERATIONAL_EVENT,
    POST_FRAME_STRATEGIC_EVENT,
    retain_events_for_frame,
)
from advoi.decision.frames import FRAMES  # noqa: E402
from advoi.memory.write_targets import (  # noqa: E402
    EVENT_WRITE_MAP,
    MemoryEventType,
    WriteTarget,
    targets_for,
)
from advoi.routing.frame_runner import FrameResult, run_frame  # noqa: E402

# One entry per decision-frame type (catalog must stay covered).
ALL_FRAME_IDS = tuple(f.id for f in FRAMES)


def test_post_frame_allowed_events_are_on_write_targets_allowlist():
    """Hook allowlist must be a non-empty subset of EVENT_WRITE_MAP."""
    assert POST_FRAME_ALLOWED_EVENTS
    for event in POST_FRAME_ALLOWED_EVENTS:
        assert event in EVENT_WRITE_MAP, f"{event} missing from EVENT_WRITE_MAP"
        assert targets_for(event), f"{event} has empty write targets"


def test_post_frame_operational_never_writes_hindsight():
    """Squad lessons stay operational (Letta/Postgres) — never Hindsight."""
    assert POST_FRAME_OPERATIONAL_EVENT is MemoryEventType.SQUAD_LESSON
    assert WriteTarget.HINDSIGHT not in targets_for(POST_FRAME_OPERATIONAL_EVENT)


def test_post_frame_strategic_writes_hindsight_only_via_map():
    """Venture beliefs are strategic and must include Hindsight in the map."""
    assert POST_FRAME_STRATEGIC_EVENT is MemoryEventType.VENTURE_BELIEF_UPDATE
    assert WriteTarget.HINDSIGHT in targets_for(POST_FRAME_STRATEGIC_EVENT)


def test_fleet_status_is_operational_only():
    """Fleet-scout tick summaries must not select strategic retain types."""
    events = retain_events_for_frame("fleet_status", "ok", has_venture=True)
    assert events == (MemoryEventType.SQUAD_LESSON,)
    assert MemoryEventType.VENTURE_BELIEF_UPDATE not in events
    for event in events:
        assert event in EVENT_WRITE_MAP
        assert WriteTarget.HINDSIGHT not in targets_for(event)


@pytest.mark.parametrize("frame_id", ALL_FRAME_IDS)
def test_retain_events_for_frame_types_on_allowlist(frame_id: str):
    """One assertion per frame type: planned retain events ⊆ write_targets."""
    events_ok = retain_events_for_frame(frame_id, "ok", has_venture=True)
    assert events_ok, f"{frame_id}: expected at least operational retain on ok"
    for event in events_ok:
        assert event in POST_FRAME_ALLOWED_EVENTS
        assert event in EVENT_WRITE_MAP
        assert targets_for(event)

    events_bad = retain_events_for_frame(frame_id, "error", has_venture=True)
    assert events_bad == ()


@pytest.mark.asyncio
async def test_run_frame_enriches_aether_detail(tmp_path, monkeypatch):
    monkeypatch.setenv("ADVOI_OPERATIONAL_STORE", str(tmp_path / "ops.jsonl"))
    monkeypatch.setenv("ADVOI_OPERATIONAL_STORE_ENABLED", "true")
    monkeypatch.setenv("LETTA_ENABLED", "false")

    result = await run_frame("fleet_status", refresh=True)
    assert result.detail.get("aether_routed") is True
    assert "venture_id" in result.detail


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "frame_id,confirmed",
    [
        ("fleet_status", False),
        ("open_briefs", False),
        ("queue_deep_review", True),
        ("systems_pulse", False),
        ("memory_health", False),
        ("guardian_status", False),
    ],
)
async def test_run_frame_retain_events_match_write_targets(
    frame_id: str, confirmed: bool, tmp_path, monkeypatch
):
    """One runtime assertion per frame type: detail retain events are map-valid."""
    monkeypatch.setenv("ADVOI_OPERATIONAL_STORE", str(tmp_path / f"ops-{frame_id}.jsonl"))
    monkeypatch.setenv("ADVOI_OPERATIONAL_STORE_ENABLED", "true")
    monkeypatch.setenv("LETTA_ENABLED", "false")

    result = await run_frame(frame_id, confirmed=confirmed, refresh=True)
    assert result.status in {"ok", "confirmation_required"}, (
        f"{frame_id}: unexpected status {result.status!r}"
    )
    assert "aether_retain_events" in result.detail

    retain_values = result.detail["aether_retain_events"]
    assert isinstance(retain_values, list)
    assert retain_values, f"{frame_id}: expected retain events on {result.status}"

    for value in retain_values:
        event = MemoryEventType(value)
        assert event in POST_FRAME_ALLOWED_EVENTS
        assert event in EVENT_WRITE_MAP
        assert targets_for(event)

    # Fleet scout must never request strategic / Hindsight-bound types.
    if frame_id == "fleet_status":
        assert MemoryEventType.VENTURE_BELIEF_UPDATE.value not in retain_values
        assert all(
            WriteTarget.HINDSIGHT not in targets_for(MemoryEventType(v))
            for v in retain_values
        )


@pytest.mark.asyncio
async def test_post_frame_aether_retains_only_allowlisted_types(tmp_path, monkeypatch):
    """Spy: every router.retain call uses an allowlisted MemoryEventType."""
    monkeypatch.setenv("ADVOI_OPERATIONAL_STORE", str(tmp_path / "ops.jsonl"))
    monkeypatch.setenv("ADVOI_OPERATIONAL_STORE_ENABLED", "true")
    monkeypatch.setenv("LETTA_ENABLED", "false")

    seen: list[MemoryEventType] = []

    async def _spy_retain(self, event_type, payload, *, session_id=None):  # noqa: ANN001
        seen.append(event_type)
        return {"spy": True}

    monkeypatch.setattr(
        "advoi.memory.router.MemoryRouter.retain",
        _spy_retain,
    )

    from advoi.aether.architect import post_frame_aether

    result = FrameResult(
        frame_id="open_briefs",
        agent_id="brief-curator",
        status="ok",
        spoken_summary="Two open briefs.",
        detail={},
    )
    await post_frame_aether(result)

    assert seen
    for event in seen:
        assert event in POST_FRAME_ALLOWED_EVENTS
        assert event in EVENT_WRITE_MAP
    assert result.detail.get("aether_retain_events") == [e.value for e in seen]
