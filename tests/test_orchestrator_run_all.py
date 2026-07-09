"""Six-agent parallel orchestration."""

from __future__ import annotations

import pytest

from advoi.routing.orchestrator import (
    ALL_SPECIALIST_FRAME_IDS,
    run_all_specialist_frames,
    synthesize_run_all_summary,
)
from advoi.routing.frame_runner import FrameResult


@pytest.mark.asyncio
async def test_run_all_specialist_frames_returns_six():
    bundle = await run_all_specialist_frames(confirmed=True, refresh=True)
    assert len(bundle.results) == 6
    assert {r.frame_id for r in bundle.results} == set(ALL_SPECIALIST_FRAME_IDS)
    assert len(bundle.agents_used) >= 6
    assert "systems_pulse" in bundle.spoken_summary.lower() or "systems check" in bundle.spoken_summary.lower()


def test_synthesize_run_all_summary_includes_diagnostics():
    results = [
        FrameResult(
            frame_id="fleet_status",
            agent_id="fleet-scout",
            status="ok",
            spoken_summary="Checking the fleet bridge now. Fleet is idle.",
            detail={},
        ),
        FrameResult(
            frame_id="open_briefs",
            agent_id="brief-curator",
            status="ok",
            spoken_summary="Pulling open briefs. No open briefs.",
            detail={},
        ),
        FrameResult(
            frame_id="memory_health",
            agent_id="memory-scout",
            status="ok",
            spoken_summary="Memory scout online. Bridge healthy.",
            detail={},
        ),
        FrameResult(
            frame_id="guardian_status",
            agent_id="guardian-sentinel",
            status="ok",
            spoken_summary="Guardian online. Confirmation on.",
            detail={},
        ),
    ]
    spoken = synthesize_run_all_summary(results)
    assert "Memory scout online" in spoken
    assert "Guardian online" in spoken