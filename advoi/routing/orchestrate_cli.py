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
    run_frames_parallel,
    run_systems_pulse,
)
from advoi.routing.slice_orchestration import (
    RunMode,
    run_slice_orchestrate,
    slice_catalog,
)


def _print_slice_payload(payload: dict) -> None:
    for row in payload["results"]:
        print(f"  {row.agent_id} / {row.frame_id}: {row.status}")
        print(f"    {row.spoken_summary[:160]}")
    print(f"summary: {payload['spoken_summary'][:280]}")
    if payload.get("mode"):
        print(f"mode: {payload['mode']}")
    if payload.get("fail_count"):
        print(f"fail_count: {payload['fail_count']}")
    squads = payload.get("squads") or {}
    if squads:
        print(f"squads: {squads.get('dispatched', 0)}/{squads.get('total', 0)} dispatched")


async def _run(
    mode: str,
    refresh: bool,
    *,
    dispatch_squads: bool = False,
    retain_memory: bool = True,
    preset_id: str | None = None,
    chain_id: str | None = None,
    slice_mode: RunMode | None = None,
) -> int:
    if mode in {"all", "prewarm"}:
        results = await prewarm_all_agents()
        print(f"prewarmed {len(results)} agents: {', '.join(AGENTS.keys())}")

    if mode == "prewarm":
        return 0

    if mode == "catalog":
        print(json.dumps(slice_catalog(), indent=2))
        return 0

    if mode in {"preset", "chain"}:
        payload = await run_slice_orchestrate(
            preset_id=preset_id if mode == "preset" else None,
            chain_id=chain_id if mode == "chain" else None,
            mode=slice_mode,
            confirmed=True,
            refresh=refresh,
            dispatch_squads=dispatch_squads,
            retain_memory=retain_memory,
        )
        if preset_id or chain_id:
            _print_slice_payload(payload)
        else:
            print("Error: --preset-id or --chain-id required", file=sys.stderr)
            return 2
        return 0

    if mode == "six-squads" or (mode in {"six", "json", "all"} and dispatch_squads):
        from advoi.squads.orchestrate import run_six_with_platform

        payload = await run_six_with_platform(
            confirmed=True,
            refresh=refresh,
            dispatch_squads=True,
            retain_memory=retain_memory,
        )
        bundle_results = payload["results"]
        if mode == "json":
            print(
                json.dumps(
                    {
                        "agents": list(AGENTS.keys()),
                        "frame_ids": list(ALL_SPECIALIST_FRAME_IDS),
                        "results": [
                            {
                                "frame_id": r.frame_id,
                                "agent_id": r.agent_id,
                                "status": r.status,
                                "spoken_summary": r.spoken_summary,
                            }
                            for r in bundle_results
                        ],
                        "agents_used": payload["agents_used"],
                        "systems": payload["systems"],
                        "spoken_summary": payload["spoken_summary"],
                        "squads": payload.get("squads"),
                    },
                    indent=2,
                )
            )
            return 0
        for row in bundle_results:
            print(f"  {row.agent_id} / {row.frame_id}: {row.status}")
            print(f"    {row.spoken_summary[:160]}")
        squads = payload.get("squads") or {}
        print(f"summary: {payload['spoken_summary'][:280]}")
        if squads:
            print(f"squads: {squads.get('dispatched', 0)}/{squads.get('total', 0)} dispatched")
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
        from advoi.squads.orchestrate import run_six_with_platform

        payload = await run_six_with_platform(
            confirmed=True,
            refresh=refresh,
            dispatch_squads=False,
            retain_memory=retain_memory,
        )
        bundle_results = payload["results"]
        if mode in {"six", "all"}:
            for row in bundle_results:
                print(f"  {row.agent_id} / {row.frame_id}: {row.status}")
                print(f"    {row.spoken_summary[:160]}")
            print(f"summary: {payload['spoken_summary'][:280]}")

        if mode == "json":
            print(
                json.dumps(
                    {
                        "agents": list(AGENTS.keys()),
                        "frame_ids": list(ALL_SPECIALIST_FRAME_IDS),
                        "results": [
                            {
                                "frame_id": r.frame_id,
                                "agent_id": r.agent_id,
                                "status": r.status,
                                "spoken_summary": r.spoken_summary,
                            }
                            for r in bundle_results
                        ],
                        "agents_used": payload["agents_used"],
                        "systems": payload["systems"],
                        "spoken_summary": payload["spoken_summary"],
                    },
                    indent=2,
                )
            )
        return 0

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ADVoi multi-agent orchestration")
    parser.add_argument(
        "mode",
        nargs="?",
        default="all",
        choices=[
            "prewarm",
            "parallel",
            "pulse",
            "six",
            "six-squads",
            "all",
            "json",
            "catalog",
            "preset",
            "chain",
        ],
        help="prewarm | parallel | pulse | six | preset | chain | catalog | ...",
    )
    parser.add_argument("--refresh", action="store_true", help="Bypass agent cache")
    parser.add_argument(
        "--dispatch-squads",
        action="store_true",
        help="Also dispatch all execution squads (with six/json/all/preset/chain)",
    )
    parser.add_argument(
        "--no-retain-memory",
        action="store_true",
        help="Skip operational memory write after multi-agent run",
    )
    parser.add_argument("--preset-id", help="Builtin slice preset id (with preset mode)")
    parser.add_argument("--chain-id", help="Builtin preset chain id (with chain mode)")
    parser.add_argument(
        "--slice-mode",
        choices=["parallel", "wave", "stagger"],
        help="Override execution mode for ad-hoc frame lists",
    )
    args = parser.parse_args()
    try:
        raise SystemExit(
            asyncio.run(
                _run(
                    args.mode,
                    args.refresh,
                    dispatch_squads=args.dispatch_squads or args.mode == "six-squads",
                    retain_memory=not args.no_retain_memory,
                    preset_id=args.preset_id,
                    chain_id=args.chain_id,
                    slice_mode=args.slice_mode,  # type: ignore[arg-type]
                )
            )
        )
    except KeyboardInterrupt:
        raise SystemExit(130) from None


if __name__ == "__main__":
    main()