"""CLI: prewarm and run multiple specialist agents in parallel."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from advoi.routing.agent_bootstrap import prewarm_all_agents
from advoi.routing.agents import AGENTS
from advoi.routing.orchestrator import (
    ALL_SPECIALIST_FRAME_IDS,
    run_all_specialist_frames,
    run_frames_parallel,
    run_systems_pulse,
)


async def _run(mode: str, refresh: bool) -> int:
    if mode in {"all", "prewarm"}:
        results = await prewarm_all_agents()
        print(f"prewarmed {len(results)} agents: {', '.join(AGENTS.keys())}")

    if mode == "prewarm":
        return 0

    if mode == "parallel":
        parallel = await run_frames_parallel(
            ["fleet_status", "open_briefs"],
            refresh=refresh,
        )
        for row in parallel:
            print(f"  {row.agent_id} / {row.frame_id}: {row.status}")
            print(f"    {row.spoken_summary[:160]}")

    if mode == "pulse":
        pulse = await run_systems_pulse(refresh=refresh)
        print(f"systems-pulse: {pulse.status}")
        print(f"  {pulse.spoken_summary[:200]}")

    if mode in {"six", "all", "json"}:
        bundle = await run_all_specialist_frames(confirmed=True, refresh=refresh)
        if mode in {"six", "all"}:
            for row in bundle.results:
                print(f"  {row.agent_id} / {row.frame_id}: {row.status}")
                print(f"    {row.spoken_summary[:160]}")
            print(f"summary: {bundle.spoken_summary[:280]}")

        if mode == "json":
            payload = {
                "agents": list(AGENTS.keys()),
                "frame_ids": list(ALL_SPECIALIST_FRAME_IDS),
                "results": [
                    {
                        "frame_id": r.frame_id,
                        "agent_id": r.agent_id,
                        "status": r.status,
                        "spoken_summary": r.spoken_summary,
                    }
                    for r in bundle.results
                ],
                "agents_used": bundle.agents_used,
                "systems": bundle.systems,
                "spoken_summary": bundle.spoken_summary,
            }
            print(json.dumps(payload, indent=2))
        return 0

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ADVoi multi-agent orchestration")
    parser.add_argument(
        "mode",
        nargs="?",
        default="all",
        choices=["prewarm", "parallel", "pulse", "six", "all", "json"],
        help="prewarm | parallel (fleet+briefs) | pulse | six (all 6 frames) | all | json",
    )
    parser.add_argument("--refresh", action="store_true", help="Bypass agent cache")
    args = parser.parse_args()
    try:
        raise SystemExit(asyncio.run(_run(args.mode, args.refresh)))
    except KeyboardInterrupt:
        raise SystemExit(130) from None


if __name__ == "__main__":
    main()