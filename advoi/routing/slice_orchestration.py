"""Agent slice presets, wave plans, and sequenced frame execution (PWA mirror)."""

from __future__ import annotations

import asyncio
from typing import Any, Literal

from advoi.decision.frames import FrameId, get_frame

RunMode = Literal["parallel", "wave", "stagger"]

DEFAULT_SIX_FRAME_IDS: tuple[str, ...] = (
    "fleet_status",
    "open_briefs",
    "queue_deep_review",
    "systems_pulse",
    "memory_health",
    "guardian_status",
)

SLICE_PRESETS: list[dict[str, Any]] = [
    {
        "id": "morning_pulse",
        "label": "Morning pulse",
        "frameIds": ["systems_pulse"],
        "mode": "stagger",
    },
    {
        "id": "ops_core",
        "label": "Ops core",
        "frameIds": ["fleet_status", "open_briefs", "guardian_status"],
        "mode": "wave",
    },
    {
        "id": "intel",
        "label": "Intel",
        "frameIds": ["open_briefs", "queue_deep_review", "memory_health"],
        "mode": "wave",
    },
    {
        "id": "full_six",
        "label": "Full six",
        "frameIds": list(DEFAULT_SIX_FRAME_IDS),
        "mode": "parallel",
    },
]

PRESET_CHAINS: list[dict[str, Any]] = [
    {
        "id": "ops_then_intel",
        "label": "Ops → Intel",
        "presetIds": ["ops_core", "intel"],
    },
    {
        "id": "morning_then_ops",
        "label": "Pulse → Ops",
        "presetIds": ["morning_pulse", "ops_core"],
    },
    {
        "id": "morning_then_full",
        "label": "Pulse → Full 6",
        "presetIds": ["morning_pulse", "full_six"],
    },
    {
        "id": "intel_then_dispatch",
        "label": "Intel → Dispatch",
        "presetIds": ["intel"],
        "dispatchAfter": True,
    },
    {
        "id": "full_six_then_dispatch",
        "label": "Full 6 → Dispatch",
        "presetIds": ["full_six"],
        "dispatchAfter": True,
    },
]

PULSE_FRAME_ID = "systems_pulse"


def preset_by_id(preset_id: str) -> dict[str, Any] | None:
    return next((p for p in SLICE_PRESETS if p["id"] == preset_id), None)


def chain_by_id(chain_id: str) -> dict[str, Any] | None:
    return next((c for c in PRESET_CHAINS if c["id"] == chain_id), None)


def resolve_chain_presets(chain: dict[str, Any]) -> list[dict[str, Any]]:
    return [p for pid in chain["presetIds"] if (p := preset_by_id(pid)) is not None]


def wave_size_for_mode(mode: RunMode) -> int:
    if mode == "parallel":
        return 64
    if mode == "wave":
        return 2
    return 1


def chunk_frame_waves(frame_ids: list[str], mode: RunMode) -> list[list[str]]:
    size = wave_size_for_mode(mode)
    if not frame_ids:
        return []
    if mode == "parallel":
        return [list(frame_ids)]
    waves: list[list[str]] = []
    for i in range(0, len(frame_ids), size):
        waves.append(frame_ids[i : i + size])
    return waves


def describe_wave_plan(frame_ids: list[str], mode: RunMode) -> dict[str, Any]:
    waves = chunk_frame_waves(frame_ids, mode)
    short = {
        "fleet_status": "fleet",
        "open_briefs": "briefs",
        "queue_deep_review": "review",
        "systems_pulse": "pulse",
        "memory_health": "memory",
        "guardian_status": "guardian",
    }
    return {
        "mode": mode,
        "waveCount": len(waves),
        "waves": [
            {
                "index": i,
                "frameIds": wave,
                "labels": [short.get(fid, fid.replace("_", " ")[:8]) for fid in wave],
            }
            for i, wave in enumerate(waves)
        ],
    }


def order_pulse_last(frame_ids: list[str]) -> list[str]:
    """Run systems_pulse after other frames so warmth counts stay accurate."""
    if PULSE_FRAME_ID not in frame_ids:
        return list(frame_ids)
    rest = [fid for fid in frame_ids if fid != PULSE_FRAME_ID]
    return [*rest, PULSE_FRAME_ID]


def count_failed_results(results: list[Any]) -> int:
    return sum(1 for r in results if getattr(r, "status", None) in ("error", "failed"))


def slice_catalog() -> dict[str, Any]:
    return {
        "presets": SLICE_PRESETS,
        "chains": PRESET_CHAINS,
        "defaultSix": list(DEFAULT_SIX_FRAME_IDS),
    }


def resolve_slice_run(
    *,
    frame_ids: list[str] | None = None,
    preset_id: str | None = None,
    chain_id: str | None = None,
    mode: RunMode | None = None,
) -> tuple[list[str], RunMode, dict[str, Any] | None, bool]:
    """Return (frame_ids, mode, chain_meta, dispatch_after)."""
    if chain_id:
        chain = chain_by_id(chain_id)
        if not chain:
            raise ValueError(f"Unknown chain_id: {chain_id}")
        presets = resolve_chain_presets(chain)
        if not presets:
            raise ValueError(f"Chain has no presets: {chain_id}")
        return (
            [],
            mode or "parallel",
            {
                "chainId": chain_id,
                "chainLabel": chain["label"],
                "stages": presets,
                "dispatchAfter": bool(chain.get("dispatchAfter")),
            },
            bool(chain.get("dispatchAfter")),
        )
    if preset_id:
        preset = preset_by_id(preset_id)
        if not preset:
            raise ValueError(f"Unknown preset_id: {preset_id}")
        return (
            list(preset["frameIds"]),
            mode or preset.get("mode", "parallel"),
            None,
            False,
        )
    ids = list(frame_ids or DEFAULT_SIX_FRAME_IDS)
    return ids, mode or "parallel", None, False


async def run_frames_with_mode(
    frame_ids: list[str],
    mode: RunMode,
    *,
    confirmed: bool = False,
    refresh: bool = False,
) -> list[Any]:
    """Execute frames in parallel, wave (pairs), or stagger (sequential) batches."""
    from advoi.routing.frame_runner import run_frame
    from advoi.routing.orchestrator import run_frames_parallel

    ordered = order_pulse_last(frame_ids)
    valid = [fid for fid in ordered if get_frame(fid)]
    if not valid:
        return []

    waves = chunk_frame_waves(valid, mode)
    results: list[Any] = []

    for wave in waves:
        if mode == "stagger":
            for fid in wave:
                results.append(
                    await run_frame(
                        fid,  # type: ignore[arg-type]
                        confirmed=confirmed,
                        refresh=refresh,
                    )
                )
        else:
            batch = await run_frames_parallel(
                wave,  # type: ignore[arg-type]
                confirmed=confirmed,
                refresh=refresh,
            )
            results.extend(batch)

    return results


async def run_slice_orchestrate(
    *,
    frame_ids: list[str] | None = None,
    preset_id: str | None = None,
    chain_id: str | None = None,
    mode: RunMode | None = None,
    confirmed: bool = False,
    refresh: bool = False,
    dispatch_squads: bool = False,
    retain_memory: bool = True,
) -> dict[str, Any]:
    """Run preset, chain, or ad-hoc frame list with wave/stagger/parallel modes."""
    from advoi.routing.orchestrator import _bundle_from_results
    from advoi.squads.orchestrate import dispatch_all_squads, retain_orchestration_memory

    ids, run_mode, chain_meta, chain_dispatch = resolve_slice_run(
        frame_ids=frame_ids,
        preset_id=preset_id,
        chain_id=chain_id,
        mode=mode,
    )

    all_results: list[Any] = []
    wave_plan: dict[str, Any]

    if chain_meta:
        stages_meta: list[dict[str, Any]] = []
        for preset in chain_meta["stages"]:
            stage_mode: RunMode = preset.get("mode", "parallel")
            stage_ids = list(preset["frameIds"])
            stage_results = await run_frames_with_mode(
                stage_ids,
                stage_mode,
                confirmed=confirmed,
                refresh=refresh,
            )
            all_results.extend(stage_results)
            stages_meta.append(
                {
                    "presetId": preset["id"],
                    "label": preset["label"],
                    "mode": stage_mode,
                    "frameIds": stage_ids,
                    "resultCount": len(stage_results),
                    "failCount": count_failed_results(stage_results),
                }
            )
        wave_plan = {
            "mode": "chain",
            "chainId": chain_meta["chainId"],
            "chainLabel": chain_meta["chainLabel"],
            "stages": stages_meta,
        }
        response_mode = "chain"
        should_dispatch = dispatch_squads or chain_dispatch
    else:
        all_results = await run_frames_with_mode(
            ids,
            run_mode,
            confirmed=confirmed,
            refresh=refresh,
        )
        wave_plan = describe_wave_plan(ids, run_mode)
        response_mode = run_mode
        should_dispatch = dispatch_squads

    if not all_results:
        raise ValueError("No valid frame ids provided")

    bundle = _bundle_from_results(all_results)
    if retain_memory:
        await retain_orchestration_memory(bundle)

    squad_summary: dict[str, Any] | None = None
    if should_dispatch:
        squad_summary = await dispatch_all_squads(confirmed=confirmed)
        if squad_summary:
            bundle.spoken_summary = f"{bundle.spoken_summary} Squads: {squad_summary.get('dispatched', 0)}/{squad_summary.get('total', 0)} dispatched.".strip()

    return {
        "results": all_results,
        "agents_used": bundle.agents_used,
        "systems": bundle.systems,
        "spoken_summary": bundle.spoken_summary,
        "mode": response_mode,
        "wave_plan": wave_plan,
        "fail_count": count_failed_results(all_results),
        "preset_id": preset_id,
        "chain_id": chain_id,
        "squads": squad_summary,
    }