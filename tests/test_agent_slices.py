"""Unit tests for agent slice models (mirrors web/lib/agents/agentSlices.ts)."""

from __future__ import annotations

import re
import time

from advoi.routing.slice_orchestration import (
    DEFAULT_SIX_FRAME_IDS,
    PRESET_CHAINS,
    SLICE_PRESETS,
    chunk_frame_waves,
    describe_wave_plan,
    preset_by_id as _catalog_preset_by_id,
    chain_by_id as _catalog_chain_by_id,
    resolve_chain_presets as _catalog_resolve_chain_presets,
    wave_size_for_mode,
)

FRAME_SHORT = {
    "fleet_status": "fleet",
    "open_briefs": "briefs",
    "queue_deep_review": "review",
    "systems_pulse": "pulse",
    "memory_health": "memory",
    "guardian_status": "guardian",
}

DEFAULT_SIX = list(DEFAULT_SIX_FRAME_IDS)


def short_frame_label(frame_id: str) -> str:
    return FRAME_SHORT.get(frame_id, frame_id.replace("_", " ")[:8])


def format_last_run_relative(ts: str | int | float | None) -> str | None:
    if ts is None or ts == "":
        return None
    if isinstance(ts, (int, float)):
        ms = int(ts)
    else:
        try:
            ms = int(ts)
        except (ValueError, TypeError):
            return None
    now_ms = int(time.time() * 1000)
    diff_ms = now_ms - ms
    if diff_ms < 60_000:
        return "just now"
    minutes = diff_ms // 60_000
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    return f"{days}d ago"


MAX_SLICE_QUEUE_DEPTH = 5
MORNING_PULSE_FRAME_ID = "systems_pulse"

MAX_USER_PRESETS = 8


def preset_by_id(preset_id: str) -> dict | None:
    return _catalog_preset_by_id(preset_id)


def chain_by_id(chain_id: str) -> dict | None:
    return _catalog_chain_by_id(chain_id)


def resolve_chain_presets(chain: dict) -> list[dict]:
    return _catalog_resolve_chain_presets(chain)


def slugify_user_preset_id(label: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")[:32]
    return f"user_{base}" if base else "user_custom"


def trim_user_presets(presets: list[dict], max_count: int = MAX_USER_PRESETS) -> list[dict]:
    return presets[:max_count]


def is_failed_result_status(status: str | None) -> bool:
    return status in ("error", "failed")


def frame_ids_from_selected(slices: list[dict]) -> list[str]:
    return [s["frameId"] for s in slices if s.get("selected")]


def resolve_orchestrate_frame_ids(slices: list[dict], mode: str) -> list[str]:
    if mode == "all_six":
        return list(DEFAULT_SIX)
    picked = frame_ids_from_selected(slices)
    return picked if picked else list(DEFAULT_SIX)


def build_agent_slices(
    agents: list[dict],
    frames: list[dict],
    *,
    selected_ids: set[str] | None = None,
    running_frame_ids: set[str] | None = None,
    queued_frame_ids: set[str] | None = None,
    results: list[dict] | None = None,
    squad_by_agent: dict[str, list[str]] | None = None,
) -> list[dict]:
    selected_ids = selected_ids or set()
    running_frame_ids = running_frame_ids or set()
    queued_frame_ids = queued_frame_ids or set()
    results = results or []
    squad_by_agent = squad_by_agent or {}
    frame_by_agent = {f["agent_id"]: f for f in frames}
    result_by_frame = {r["frame_id"]: r for r in results}

    ordered = agents if agents else [
        {
            "id": f["agent_id"],
            "name": f.get("agent_name"),
            "frame_id": f["id"],
            "cached": False,
        }
        for f in frames
    ]

    out = []
    for agent in ordered:
        frame = frame_by_agent.get(agent["id"]) or next(
            (f for f in frames if f["id"] == agent.get("frame_id")),
            None,
        )
        frame_id = (frame or {}).get("id") or agent.get("frame_id") or agent["id"]
        result = result_by_frame.get(frame_id)
        phase = "idle"
        if frame_id in running_frame_ids:
            phase = "running"
        elif frame_id in queued_frame_ids:
            phase = "queued"
        elif result:
            status = result.get("status")
            if status in ("ok", "success"):
                phase = "ok"
            elif status:
                phase = "error" if is_failed_result_status(status) else "ok"

        last_run = agent.get("last_run") or {}
        row = {
            "agentId": agent["id"],
            "frameId": frame_id,
            "label": (frame or {}).get("label") or agent.get("name") or agent["id"],
            "shortLabel": short_frame_label(frame_id),
            "warm": bool(agent.get("cached")),
            "phase": phase,
            "lastStatus": result.get("status") if result else last_run.get("status"),
            "selected": agent["id"] in selected_ids,
            "squadIds": squad_by_agent.get(agent["id"], []),
        }
        if last_run.get("timestamp") is not None:
            row["lastRunAt"] = str(last_run["timestamp"])
        out.append(row)
    return out


def squad_membership_map(squads: list[dict]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for squad in squads:
        for aid in squad["agent_ids"]:
            out.setdefault(aid, []).append(squad["id"])
    return out


def frame_ids_for_squad_agent_ids(agent_ids: list[str], frames: list[dict]) -> list[str]:
    by_agent = {f["agent_id"]: f["id"] for f in frames}
    ids: list[str] = []
    for aid in agent_ids:
        fid = by_agent.get(aid)
        if fid:
            ids.append(fid)
    return ids


def frame_ids_for_squad_slice(squad: dict, frames: list[dict]) -> list[str]:
    return frame_ids_for_squad_agent_ids(squad["agentIds"], frames)


def run_progress_model(
    mode: str,
    wave_index: int,
    waves: list[list[str]],
    completed_in_current_wave: int,
) -> dict:
    total_frames = sum(len(w) for w in waves)
    completed_frames = sum(len(waves[i]) for i in range(wave_index))
    completed_frames += completed_in_current_wave
    percent = round((completed_frames / total_frames) * 100) if total_frames else 0
    return {
        "mode": mode,
        "waveIndex": wave_index,
        "waveCount": len(waves),
        "completedFrames": completed_frames,
        "totalFrames": total_frames,
        "percent": percent,
    }


def frame_ids_from_failed_results(results: list[dict]) -> list[str]:
    return [
        r["frame_id"]
        for r in results
        if is_failed_result_status(r.get("status"))
    ]


def count_failed_results(results: list[dict]) -> int:
    return len(frame_ids_from_failed_results(results))


def squad_run_progress_model(
    completed_squads: int,
    total_squads: int,
    completed_frames: int,
    total_frames: int,
) -> dict:
    percent = round((completed_frames / total_frames) * 100) if total_frames else 0
    squad_percent = round((completed_squads / total_squads) * 100) if total_squads else 0
    return {
        "completedSquads": completed_squads,
        "totalSquads": total_squads,
        "completedFrames": completed_frames,
        "totalFrames": total_frames,
        "percent": percent,
        "squadPercent": squad_percent,
    }


def merge_orchestrate_payloads(payloads: list[dict]) -> dict:
    results: list[dict] = []
    agents_used: list[str] = []
    systems: list[str] = []
    spoken_parts: list[str] = []
    last_squads = None
    for p in payloads:
        results.extend(p.get("results") or [])
        agents_used.extend(p.get("agents_used") or [])
        systems.extend(p.get("systems") or [])
        if p.get("spoken_summary"):
            spoken_parts.append(p["spoken_summary"])
        if p.get("squads") is not None:
            last_squads = p["squads"]
    out: dict = {
        "results": results,
        "agents_used": list(dict.fromkeys(agents_used)),
        "systems": list(dict.fromkeys(systems)),
        "spoken_summary": " ".join(spoken_parts),
    }
    if last_squads is not None:
        out["squads"] = last_squads
    return out


def build_result_rows(slices: list[dict], results: list[dict]) -> list[dict]:
    by_frame = {r["frame_id"]: r for r in results}
    rows: list[dict] = []
    for s in slices:
        r = by_frame.get(s["frameId"])
        if not r:
            continue
        rows.append(
            {
                "frameId": s["frameId"],
                "agentId": s["agentId"],
                "shortLabel": s["shortLabel"],
                "label": s["label"],
                "status": r["status"],
                "spokenSummary": r.get("spoken_summary"),
            }
        )
    return rows


def test_short_frame_label() -> None:
    assert short_frame_label("fleet_status") == "fleet"
    assert short_frame_label("unknown_frame_id") == "unknown "


def test_resolve_all_six() -> None:
    assert resolve_orchestrate_frame_ids([], "all_six") == DEFAULT_SIX


def test_resolve_selected_fallback() -> None:
    slices = [{"frameId": "fleet_status", "selected": False}]
    assert resolve_orchestrate_frame_ids(slices, "selected") == DEFAULT_SIX


def test_resolve_selected_picked() -> None:
    slices = [
        {"frameId": "fleet_status", "selected": True},
        {"frameId": "open_briefs", "selected": True},
    ]
    assert resolve_orchestrate_frame_ids(slices, "selected") == [
        "fleet_status",
        "open_briefs",
    ]


def test_build_slices_failed_phase() -> None:
    agents = [{"id": "systems-pulse", "cached": False}]
    frames = [
        {
            "id": "systems_pulse",
            "label": "Systems pulse",
            "agent_id": "systems-pulse",
        }
    ]
    slices = build_agent_slices(
        agents,
        frames,
        results=[{"frame_id": "systems_pulse", "status": "failed"}],
    )
    assert slices[0]["phase"] == "error"


def test_build_slices_running_phase() -> None:
    agents = [{"id": "fleet-scout", "cached": True}]
    frames = [
        {
            "id": "fleet_status",
            "label": "Fleet status",
            "agent_id": "fleet-scout",
        }
    ]
    slices = build_agent_slices(
        agents,
        frames,
        running_frame_ids={"fleet_status"},
    )
    assert len(slices) == 1
    assert slices[0]["phase"] == "running"
    assert slices[0]["warm"] is True


def test_build_slices_queued_phase() -> None:
    agents = [{"id": "fleet-scout"}]
    frames = [
        {
            "id": "fleet_status",
            "label": "Fleet status",
            "agent_id": "fleet-scout",
        }
    ]
    slices = build_agent_slices(
        agents,
        frames,
        queued_frame_ids={"fleet_status"},
    )
    assert slices[0]["phase"] == "queued"


def test_build_slices_running_overrides_queued() -> None:
    agents = [{"id": "fleet-scout"}]
    frames = [
        {
            "id": "fleet_status",
            "label": "Fleet status",
            "agent_id": "fleet-scout",
        }
    ]
    slices = build_agent_slices(
        agents,
        frames,
        running_frame_ids={"fleet_status"},
        queued_frame_ids={"fleet_status"},
    )
    assert slices[0]["phase"] == "running"


def test_build_slices_squad_ids() -> None:
    agents = [{"id": "fleet-scout"}, {"id": "briefs-bot"}]
    frames = [
        {"id": "fleet_status", "label": "Fleet", "agent_id": "fleet-scout"},
        {"id": "open_briefs", "label": "Briefs", "agent_id": "briefs-bot"},
    ]
    slices = build_agent_slices(
        agents,
        frames,
        squad_by_agent={"fleet-scout": ["alpha", "beta"]},
    )
    assert slices[0]["squadIds"] == ["alpha", "beta"]
    assert slices[1]["squadIds"] == []


def test_squad_membership_map() -> None:
    squads = [
        {"id": "alpha", "agent_ids": ["a1", "a2"]},
        {"id": "beta", "agent_ids": ["a2", "a3"]},
    ]
    assert squad_membership_map(squads) == {
        "a1": ["alpha"],
        "a2": ["alpha", "beta"],
        "a3": ["beta"],
    }


def test_wave_size_for_mode() -> None:
    assert wave_size_for_mode("parallel") == 64
    assert wave_size_for_mode("wave") == 2
    assert wave_size_for_mode("stagger") == 1


def test_chunk_frame_waves_empty() -> None:
    assert chunk_frame_waves([], "wave") == []


def test_chunk_frame_waves_parallel() -> None:
    ids = ["a", "b", "c", "d", "e"]
    assert chunk_frame_waves(ids, "parallel") == [ids]


def test_chunk_frame_waves_wave() -> None:
    ids = ["a", "b", "c", "d", "e"]
    assert chunk_frame_waves(ids, "wave") == [["a", "b"], ["c", "d"], ["e"]]


def test_chunk_frame_waves_stagger() -> None:
    ids = ["a", "b", "c"]
    assert chunk_frame_waves(ids, "stagger") == [["a"], ["b"], ["c"]]


def test_frame_ids_for_squad_agent_ids() -> None:
    frames = [
        {"id": "fleet_status", "agent_id": "fleet-scout"},
        {"id": "open_briefs", "agent_id": "briefs-bot"},
    ]
    assert frame_ids_for_squad_agent_ids(
        ["fleet-scout", "missing", "briefs-bot"],
        frames,
    ) == ["fleet_status", "open_briefs"]


def test_frame_ids_for_squad_slice() -> None:
    frames = [
        {"id": "fleet_status", "agent_id": "fleet-scout"},
        {"id": "open_briefs", "agent_id": "briefs-bot"},
    ]
    squad = {"agentIds": ["fleet-scout", "briefs-bot"]}
    assert frame_ids_for_squad_slice(squad, frames) == [
        "fleet_status",
        "open_briefs",
    ]


def test_run_progress_model() -> None:
    waves = [["a", "b"], ["c"]]
    assert run_progress_model("wave", 0, waves, 1) == {
        "mode": "wave",
        "waveIndex": 0,
        "waveCount": 2,
        "completedFrames": 1,
        "totalFrames": 3,
        "percent": 33,
    }
    assert run_progress_model("wave", 1, waves, 1) == {
        "mode": "wave",
        "waveIndex": 1,
        "waveCount": 2,
        "completedFrames": 3,
        "totalFrames": 3,
        "percent": 100,
    }
    assert run_progress_model("parallel", 0, [[]], 0)["percent"] == 0


def test_merge_orchestrate_payloads() -> None:
    merged = merge_orchestrate_payloads(
        [
            {
                "results": [{"frame_id": "a", "status": "ok"}],
                "agents_used": ["x", "y"],
                "systems": ["s1"],
                "spoken_summary": "first",
                "squads": {"dispatched": 1, "total": 2},
            },
            {
                "results": [{"frame_id": "b", "status": "error"}],
                "agents_used": ["y", "z"],
                "systems": ["s1", "s2"],
                "spoken_summary": "second",
            },
        ]
    )
    assert merged["results"] == [
        {"frame_id": "a", "status": "ok"},
        {"frame_id": "b", "status": "error"},
    ]
    assert merged["agents_used"] == ["x", "y", "z"]
    assert merged["systems"] == ["s1", "s2"]
    assert merged["spoken_summary"] == "first second"
    assert merged["squads"] == {"dispatched": 1, "total": 2}


def test_frame_ids_from_failed_results() -> None:
    results = [
        {"frame_id": "fleet_status", "status": "ok"},
        {"frame_id": "open_briefs", "status": "error"},
        {"frame_id": "systems_pulse", "status": "failed"},
        {"frame_id": "memory_health", "status": "success"},
    ]
    assert frame_ids_from_failed_results(results) == [
        "open_briefs",
        "systems_pulse",
    ]


def test_count_failed_results() -> None:
    results = [
        {"frame_id": "a", "status": "ok"},
        {"frame_id": "b", "status": "error"},
        {"frame_id": "c", "status": "failed"},
    ]
    assert count_failed_results(results) == 2
    assert count_failed_results([]) == 0


def test_describe_wave_plan_wave_mode() -> None:
    frame_ids = list(DEFAULT_SIX)
    plan = describe_wave_plan(frame_ids, "wave")
    assert plan["mode"] == "wave"
    assert plan["waveCount"] == 3
    assert len(plan["waves"]) == 3
    assert plan["waves"][0] == {
        "index": 0,
        "frameIds": ["fleet_status", "open_briefs"],
        "labels": ["fleet", "briefs"],
    }
    assert plan["waves"][2]["index"] == 2
    assert plan["waves"][2]["frameIds"] == ["memory_health", "guardian_status"]


def test_describe_wave_plan_parallel() -> None:
    frame_ids = ["fleet_status", "open_briefs", "systems_pulse"]
    plan = describe_wave_plan(frame_ids, "parallel")
    assert plan["waveCount"] == 1
    assert plan["waves"] == [
        {
            "index": 0,
            "frameIds": frame_ids,
            "labels": ["fleet", "briefs", "pulse"],
        }
    ]


def test_describe_wave_plan_empty() -> None:
    plan = describe_wave_plan([], "stagger")
    assert plan == {"mode": "stagger", "waveCount": 0, "waves": []}


def test_squad_run_progress_model() -> None:
    assert squad_run_progress_model(0, 3, 0, 12) == {
        "completedSquads": 0,
        "totalSquads": 3,
        "completedFrames": 0,
        "totalFrames": 12,
        "percent": 0,
        "squadPercent": 0,
    }
    assert squad_run_progress_model(1, 3, 4, 12) == {
        "completedSquads": 1,
        "totalSquads": 3,
        "completedFrames": 4,
        "totalFrames": 12,
        "percent": 33,
        "squadPercent": 33,
    }
    assert squad_run_progress_model(3, 3, 12, 12) == {
        "completedSquads": 3,
        "totalSquads": 3,
        "completedFrames": 12,
        "totalFrames": 12,
        "percent": 100,
        "squadPercent": 100,
    }
    assert squad_run_progress_model(0, 0, 0, 0)["percent"] == 0
    assert squad_run_progress_model(0, 0, 0, 0)["squadPercent"] == 0


def test_format_last_run_relative_just_now() -> None:
    now_ms = int(time.time() * 1000)
    assert format_last_run_relative(now_ms) == "just now"
    assert format_last_run_relative(now_ms - 30_000) == "just now"


def test_format_last_run_relative_minutes() -> None:
    now_ms = int(time.time() * 1000)
    label = format_last_run_relative(now_ms - 5 * 60_000)
    assert label is not None
    assert re.fullmatch(r"\d+m ago", label)
    assert label == "5m ago"


def test_format_last_run_relative_invalid() -> None:
    assert format_last_run_relative(None) is None
    assert format_last_run_relative("") is None
    assert format_last_run_relative("not-a-timestamp") is None


def test_preset_by_id_morning_pulse() -> None:
    preset = preset_by_id("morning_pulse")
    assert preset is not None
    assert preset["frameIds"] == ["systems_pulse"]
    assert preset["mode"] == "stagger"


def test_preset_ops_core_and_intel_frames() -> None:
    ops = preset_by_id("ops_core")
    assert ops is not None
    assert ops["frameIds"] == [
        "fleet_status",
        "open_briefs",
        "guardian_status",
    ]
    assert ops["mode"] == "wave"
    intel = preset_by_id("intel")
    assert intel is not None
    assert intel["frameIds"] == [
        "open_briefs",
        "queue_deep_review",
        "memory_health",
    ]


def test_preset_full_six_parallel() -> None:
    preset = preset_by_id("full_six")
    assert preset is not None
    assert preset["frameIds"] == DEFAULT_SIX
    assert preset["mode"] == "parallel"
    assert preset_by_id("missing") is None


def test_build_slices_last_run_at() -> None:
    agents = [
        {
            "id": "fleet-scout",
            "last_run": {"status": "ok", "timestamp": 1710000000000},
        }
    ]
    frames = [
        {
            "id": "fleet_status",
            "label": "Fleet status",
            "agent_id": "fleet-scout",
        }
    ]
    slices = build_agent_slices(agents, frames)
    assert slices[0]["lastRunAt"] == "1710000000000"


def test_build_result_rows() -> None:
    slices = [
        {
            "agentId": "fleet-scout",
            "frameId": "fleet_status",
            "shortLabel": "fleet",
            "label": "Fleet status",
        },
        {
            "agentId": "briefs-bot",
            "frameId": "open_briefs",
            "shortLabel": "briefs",
            "label": "Open briefs",
        },
    ]
    results = [
        {
            "frame_id": "fleet_status",
            "status": "ok",
            "spoken_summary": "All clear",
        }
    ]
    rows = build_result_rows(slices, results)
    assert len(rows) == 1
    assert rows[0] == {
        "frameId": "fleet_status",
        "agentId": "fleet-scout",
        "shortLabel": "fleet",
        "label": "Fleet status",
        "status": "ok",
        "spokenSummary": "All clear",
    }


def test_preset_chain_ops_then_intel() -> None:
    chain = chain_by_id("ops_then_intel")
    assert chain is not None
    presets = resolve_chain_presets(chain)
    assert len(presets) == 2
    assert presets[0]["id"] == "ops_core"
    assert presets[1]["id"] == "intel"
    assert chain_by_id("missing") is None


def test_preset_chain_morning_then_ops() -> None:
    chain = chain_by_id("morning_then_ops")
    assert chain is not None
    presets = resolve_chain_presets(chain)
    assert len(presets) == 2
    assert presets[0]["id"] == "morning_pulse"
    assert presets[1]["id"] == "ops_core"


def test_preset_chain_full_six_dispatch_after() -> None:
    chain = chain_by_id("full_six_then_dispatch")
    assert chain is not None
    assert chain.get("dispatchAfter") is True
    presets = resolve_chain_presets(chain)
    assert len(presets) == 1
    assert presets[0]["id"] == "full_six"


def test_preset_chain_morning_then_full() -> None:
    chain = chain_by_id("morning_then_full")
    assert chain is not None
    presets = resolve_chain_presets(chain)
    assert len(presets) == 2
    assert presets[0]["id"] == "morning_pulse"
    assert presets[1]["id"] == "full_six"


def test_preset_chain_intel_then_dispatch() -> None:
    chain = chain_by_id("intel_then_dispatch")
    assert chain is not None
    assert chain.get("dispatchAfter") is True
    presets = resolve_chain_presets(chain)
    assert len(presets) == 1
    assert presets[0]["id"] == "intel"


def test_preset_chains_count_five() -> None:
    assert len(PRESET_CHAINS) == 5


def enqueue_slice_run(queue: list[dict], entry: dict, max_depth: int = MAX_SLICE_QUEUE_DEPTH) -> list[dict]:
    next_q = [*queue, entry]
    if len(next_q) <= max_depth:
        return next_q
    return next_q[len(next_q) - max_depth :]


def dequeue_slice_run(queue: list[dict]) -> tuple[list[dict], dict | None]:
    if not queue:
        return queue, None
    head, *rest = queue
    return rest, head


def should_mirror_voice_frame(detail: dict | None) -> bool:
    if not detail or not detail.get("frameId"):
        return False
    if detail.get("source") == "agents_orchestrator":
        return False
    return True


def frame_id_to_preset_id(frame_id: str) -> str | None:
    if frame_id == MORNING_PULSE_FRAME_ID:
        return "morning_pulse"
    return None


def test_slice_run_queue_enqueue_dequeue() -> None:
    q: list[dict] = []
    q = enqueue_slice_run(q, {"id": "1", "label": "A"})
    q = enqueue_slice_run(q, {"id": "2", "label": "B"})
    assert len(q) == 2
    q, nxt = dequeue_slice_run(q)
    assert nxt is not None
    assert nxt["label"] == "A"
    assert len(q) == 1


def test_slice_run_queue_caps_at_max_depth() -> None:
    q: list[dict] = []
    for i in range(7):
        q = enqueue_slice_run(q, {"id": str(i), "label": f"run-{i}"})
    assert len(q) == MAX_SLICE_QUEUE_DEPTH
    assert q[0]["label"] == "run-2"


def test_should_mirror_voice_frame() -> None:
    assert should_mirror_voice_frame({"frameId": "systems_pulse", "source": "morning_pulse_cta"})
    assert not should_mirror_voice_frame({"frameId": "systems_pulse", "source": "agents_orchestrator"})
    assert not should_mirror_voice_frame(None)


def test_frame_id_to_preset_id_morning_pulse() -> None:
    assert frame_id_to_preset_id(MORNING_PULSE_FRAME_ID) == "morning_pulse"
    assert frame_id_to_preset_id("fleet_status") is None


def detect_voice_mirror_complete(
    frame_id: str,
    agents: list[dict],
    started_at_ms: int,
) -> bool:
    agent = next((a for a in agents if a.get("frame_id") == frame_id), None)
    ts = (agent or {}).get("last_run", {}).get("timestamp")
    if ts is None:
        return False
    run_ms = int(ts) if isinstance(ts, (int, float)) else int(str(ts))
    return run_ms >= started_at_ms


def voice_mirror_result_from_agent(frame_id: str, agents: list[dict]) -> dict | None:
    agent = next((a for a in agents if a.get("frame_id") == frame_id), None)
    if not agent or not agent.get("last_run"):
        return None
    lr = agent["last_run"]
    return {
        "frame_id": frame_id,
        "agent_id": agent.get("id"),
        "status": lr.get("status"),
        "spoken_summary": lr.get("spoken_summary"),
    }


def remove_queue_item(queue: list[dict], item_id: str) -> list[dict]:
    return [q for q in queue if q.get("id") != item_id]


def bump_queue_item(queue: list[dict], item_id: str) -> list[dict]:
    idx = next((i for i, q in enumerate(queue) if q.get("id") == item_id), -1)
    if idx <= 0:
        return queue
    item = queue[idx]
    rest = [q for i, q in enumerate(queue) if i != idx]
    return [item, *rest]


def move_queue_item(queue: list[dict], item_id: str, direction: str) -> list[dict]:
    idx = next((i for i, q in enumerate(queue) if q.get("id") == item_id), -1)
    if idx < 0:
        return queue
    target = idx - 1 if direction == "up" else idx + 1
    if target < 0 or target >= len(queue):
        return queue
    next_q = list(queue)
    next_q[idx], next_q[target] = next_q[target], next_q[idx]
    return next_q


def reorder_queue_item(queue: list[dict], item_id: str, to_index: int) -> list[dict]:
    from_index = next((i for i, q in enumerate(queue) if q.get("id") == item_id), -1)
    if from_index < 0:
        return queue
    clamped = max(0, min(to_index, len(queue) - 1))
    if from_index == clamped:
        return queue
    next_q = list(queue)
    item = next_q.pop(from_index)
    next_q.insert(clamped, item)
    return next_q


def is_failed_mirror_status(status: str | None) -> bool:
    return status in ("error", "failed")


def voice_mirror_log_label(frame_id: str, source: str | None = None) -> str:
    preset_id = frame_id_to_preset_id(frame_id)
    preset = preset_by_id(preset_id) if preset_id else None
    base = preset["label"] if preset else frame_id.replace("_", " ")
    src = (source or "voice").replace("_", " ")
    return f"Voice: {base} ({src})"


def voice_mirror_log_mode(frame_id: str) -> str:
    preset_id = frame_id_to_preset_id(frame_id)
    preset = preset_by_id(preset_id or "")
    return preset["mode"] if preset else "stagger"


def export_user_chains_json(chains: list[dict]) -> str:
    import json

    return json.dumps({"version": 1, "exportedAt": 0, "chains": chains}, indent=2)


def export_orchestration_bundle(
    presets: list[dict],
    chains: list[dict],
    history: list[dict],
    run_mode: str | None = None,
) -> str:
    import json

    payload: dict = {
        "version": 1,
        "exportedAt": 0,
        "presets": presets,
        "chains": chains,
        "history": history,
    }
    if run_mode:
        payload["runMode"] = run_mode
    return json.dumps(payload, indent=2)


MORNING_PULSE_CHAIN_IDS = ("morning_then_ops", "morning_then_full")


def voice_mirror_chain_suggestions(frame_id: str, status: str | None = None) -> list[dict]:
    if is_failed_mirror_status(status):
        return []
    if frame_id_to_preset_id(frame_id) != "morning_pulse":
        return []
    out: list[dict] = []
    for chain_id in MORNING_PULSE_CHAIN_IDS:
        chain = chain_by_id(chain_id)
        if chain:
            out.append({"chainId": chain["id"], "label": chain["label"]})
    return out


def voice_mirror_chain_suggestion(frame_id: str, status: str | None = None) -> dict | None:
    suggestions = voice_mirror_chain_suggestions(frame_id, status)
    return suggestions[0] if suggestions else None


def describe_bundle_import(sections: list[str]) -> str:
    labels = {"presets": "presets", "chains": "chains", "history": "history", "runMode": "run mode"}
    if not sections:
        return "Nothing imported"
    return f"Imported {', '.join(labels.get(s, s) for s in sections)}"


def chain_draft_label(preset_ids: list[str], presets: list[dict]) -> str:
    by_id = {p["id"]: p["label"] for p in presets}
    return " → ".join(by_id.get(pid, pid) for pid in preset_ids)


MAX_USER_CHAINS = 6


def test_detect_voice_mirror_complete() -> None:
    agents = [
        {
            "id": "systems-pulse",
            "frame_id": MORNING_PULSE_FRAME_ID,
            "last_run": {"status": "ok", "timestamp": 2000},
        }
    ]
    assert detect_voice_mirror_complete(MORNING_PULSE_FRAME_ID, agents, 1000)
    assert not detect_voice_mirror_complete(MORNING_PULSE_FRAME_ID, agents, 3000)


def test_voice_mirror_result_from_agent() -> None:
    agents = [
        {
            "id": "systems-pulse",
            "frame_id": MORNING_PULSE_FRAME_ID,
            "last_run": {"status": "ok", "spoken_summary": "Pulse ok", "timestamp": 2000},
        }
    ]
    result = voice_mirror_result_from_agent(MORNING_PULSE_FRAME_ID, agents)
    assert result is not None
    assert result["spoken_summary"] == "Pulse ok"


def test_queue_remove_and_bump() -> None:
    q = [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}, {"id": "c", "label": "C"}]
    q = remove_queue_item(q, "b")
    assert [x["label"] for x in q] == ["A", "C"]
    q = bump_queue_item(q, "c")
    assert [x["label"] for x in q] == ["C", "A"]


def test_queue_move_up_down() -> None:
    q = [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}, {"id": "c", "label": "C"}]
    q = move_queue_item(q, "b", "up")
    assert [x["label"] for x in q] == ["B", "A", "C"]
    q = move_queue_item(q, "a", "down")
    assert [x["label"] for x in q] == ["B", "C", "A"]
    assert [x["label"] for x in move_queue_item(q, "b", "up")] == ["B", "C", "A"]


def test_voice_mirror_log_helpers() -> None:
    assert is_failed_mirror_status("error")
    assert is_failed_mirror_status("failed")
    assert not is_failed_mirror_status("ok")
    label = voice_mirror_log_label(MORNING_PULSE_FRAME_ID, "morning_pulse_cta")
    assert "Morning pulse" in label
    assert "morning pulse cta" in label
    assert voice_mirror_log_mode(MORNING_PULSE_FRAME_ID) == "stagger"
    assert voice_mirror_log_mode("fleet_status") == "stagger"


def test_export_user_chains_json() -> None:
    chains = [
        {
            "id": "uchain_ops_intel",
            "label": "Ops → Intel → Dispatch",
            "presetIds": ["ops_core", "intel"],
            "dispatchAfter": True,
            "source": "user",
        }
    ]
    raw = export_user_chains_json(chains)
    assert '"version": 1' in raw
    assert "uchain_ops_intel" in raw
    assert "dispatchAfter" in raw


def test_export_orchestration_bundle() -> None:
    raw = export_orchestration_bundle(
        presets=[{"id": "user_test", "label": "Test", "frameIds": ["fleet_status"], "mode": "wave"}],
        chains=[],
        history=[{"id": "run-1", "label": "Ops", "mode": "wave", "frameCount": 1, "okCount": 1, "failCount": 0}],
        run_mode="wave",
    )
    assert '"presets"' in raw
    assert '"chains"' in raw
    assert '"history"' in raw
    assert '"runMode": "wave"' in raw


def test_voice_mirror_chain_suggestion() -> None:
    suggestion = voice_mirror_chain_suggestion(MORNING_PULSE_FRAME_ID, "ok")
    assert suggestion is not None
    assert suggestion["chainId"] == "morning_then_ops"
    assert "Pulse" in suggestion["label"]
    assert voice_mirror_chain_suggestion(MORNING_PULSE_FRAME_ID, "error") is None
    assert voice_mirror_chain_suggestion("fleet_status", "ok") is None


def test_voice_mirror_chain_suggestions_plural() -> None:
    suggestions = voice_mirror_chain_suggestions(MORNING_PULSE_FRAME_ID, "ok")
    assert len(suggestions) == 2
    assert suggestions[0]["chainId"] == "morning_then_ops"
    assert suggestions[1]["chainId"] == "morning_then_full"
    assert voice_mirror_chain_suggestions(MORNING_PULSE_FRAME_ID, "error") == []


def test_reorder_queue_item() -> None:
    q = [
        {"id": "a", "label": "A"},
        {"id": "b", "label": "B"},
        {"id": "c", "label": "C"},
    ]
    reordered = reorder_queue_item(q, "c", 0)
    assert [x["label"] for x in reordered] == ["C", "A", "B"]


SLICE_QUICK_PICKS = [
    {"id": "all", "label": "All 6", "action": "all"},
    {"id": "ops", "label": "Ops", "presetId": "ops_core"},
    {"id": "intel", "label": "Intel", "presetId": "intel"},
    {"id": "pulse", "label": "Pulse", "presetId": "morning_pulse"},
    {"id": "clear", "label": "Clear", "action": "clear"},
]


def quick_pick_by_id(pick_id: str) -> dict | None:
    return next((p for p in SLICE_QUICK_PICKS if p["id"] == pick_id), None)


def agent_ids_for_frame_ids(frame_ids: list[str], slices: list[dict]) -> list[str]:
    wanted = set(frame_ids)
    return [s["agentId"] for s in slices if s.get("frameId") in wanted]


def agent_ids_for_quick_pick(pick: dict, slices: list[dict]) -> list[str]:
    if pick.get("action") == "clear":
        return []
    if pick.get("action") == "all":
        return agent_ids_for_frame_ids(list(DEFAULT_SIX), slices)
    preset_id = pick.get("presetId")
    if preset_id:
        preset = preset_by_id(preset_id)
        if preset:
            return agent_ids_for_frame_ids(list(preset["frameIds"]), slices)
    return []


def active_wave_labels(running_frame_ids: list[str]) -> str:
    return " · ".join(short_frame_label(fid) for fid in running_frame_ids)


def test_slice_quick_picks() -> None:
    assert len(SLICE_QUICK_PICKS) == 5
    slices = [
        {"agentId": f"agent-{i}", "frameId": fid}
        for i, fid in enumerate(DEFAULT_SIX)
    ]
    ops_pick = quick_pick_by_id("ops")
    assert ops_pick is not None
    assert len(agent_ids_for_quick_pick(ops_pick, slices)) == 3
    all_pick = quick_pick_by_id("all")
    assert all_pick is not None
    assert len(agent_ids_for_quick_pick(all_pick, slices)) == 6


def test_active_wave_labels() -> None:
    assert active_wave_labels(["fleet_status", "open_briefs"]) == "fleet · briefs"


def test_describe_bundle_import() -> None:
    assert "presets" in describe_bundle_import(["presets", "chains"])
    assert describe_bundle_import([]) == "Nothing imported"


def test_chain_draft_label() -> None:
    label = chain_draft_label(["morning_pulse", "ops_core"], SLICE_PRESETS)
    assert "Morning pulse" in label
    assert "Ops core" in label


def test_max_user_chains_cap() -> None:
    assert MAX_USER_CHAINS == 6


def squad_ids_for_agent(agent_id: str, squads: list[dict]) -> list[str]:
    return [s["id"] for s in squads if agent_id in s.get("agent_ids", [])]


def test_squad_ids_for_agent() -> None:
    squads = [
        {"id": "alpha", "agent_ids": ["fleet-scout", "briefs-bot"]},
        {"id": "beta", "agent_ids": ["systems-pulse"]},
    ]
    assert squad_ids_for_agent("fleet-scout", squads) == ["alpha"]
    assert squad_ids_for_agent("missing", squads) == []


def test_append_slice_log_includes_frame_ids() -> None:
    entry = {
        "label": "Ops",
        "mode": "wave",
        "frameCount": 2,
        "okCount": 2,
        "failCount": 0,
        "frameIds": ["fleet_status", "open_briefs"],
    }
    assert entry["frameIds"] == ["fleet_status", "open_briefs"]


def test_read_preferred_run_mode_valid() -> None:
    valid = {"parallel", "wave", "stagger"}
    assert "wave" in valid


def test_slice_run_log_entry_stores_frame_ids() -> None:
    entry = {
        "id": "run-1",
        "ts": 1710000000000,
        "label": "Ops core",
        "mode": "wave",
        "frameCount": 3,
        "okCount": 3,
        "failCount": 0,
        "frameIds": ["fleet_status", "open_briefs", "guardian_status"],
    }
    assert entry["frameIds"] is not None
    assert len(entry["frameIds"]) == 3


def test_slugify_user_preset_id() -> None:
    assert slugify_user_preset_id("Fleet + Briefs") == "user_fleet_briefs"
    assert slugify_user_preset_id("!!!") == "user_custom"


def test_trim_user_presets_max_eight() -> None:
    presets = [{"id": f"user_{i}"} for i in range(12)]
    trimmed = trim_user_presets(presets)
    assert len(trimmed) == MAX_USER_PRESETS


def test_all_presets_for_bar_merges() -> None:
    user = [{"id": "user_custom", "label": "Custom", "frameIds": ["fleet_status"], "mode": "wave"}]
    merged = [*SLICE_PRESETS, *user]
    assert len(merged) == len(SLICE_PRESETS) + 1
    assert merged[-1]["id"] == "user_custom"


def _frame_sets_equal(a: list[str], b: list[str]) -> bool:
    return set(a) == set(b) and len(a) == len(b)


def _chain_follow_up(chain_id: str, stack: bool = False) -> dict | None:
    chain = chain_by_id(chain_id)
    if not chain:
        return None
    return {
        "id": f"stack_{chain_id}" if stack else f"run_{chain_id}",
        "label": f"Stack {chain['label']}" if stack else chain["label"],
        "action": {
            "kind": "stack_chain" if stack else "run_chain",
            "chainId": chain_id,
        },
    }


def _queue_follow_up(queue_depth: int) -> dict:
    return {
        "id": "run_queue",
        "label": f"Run queue ({queue_depth})",
        "action": {"kind": "run_queue"},
    }


DISPATCH_ALL_FOLLOW_UP = {
    "id": "dispatch_all",
    "label": "Dispatch all squads",
    "action": {"kind": "dispatch_all"},
}


def post_run_follow_ups(
    frame_ids: list[str],
    fail_count: int,
    *,
    queue_depth: int = 0,
    squads_dispatched: bool = False,
) -> list[dict]:
    if fail_count > 0:
        out = [
            {
                "id": "retry_stagger",
                "label": "Retry failed (stagger)",
                "action": {"kind": "retry_stagger"},
            }
        ]
        if queue_depth > 0:
            out.append(_queue_follow_up(queue_depth))
        return out
    if not frame_ids:
        return [_queue_follow_up(queue_depth)] if queue_depth > 0 else []

    out: list[dict] = []

    morning = preset_by_id("morning_pulse")
    if morning and _frame_sets_equal(frame_ids, list(morning["frameIds"])):
        out.extend(
            x
            for x in [
                _chain_follow_up("morning_then_ops"),
                _chain_follow_up("morning_then_full"),
                _chain_follow_up("morning_then_ops", stack=True),
            ]
            if x is not None
        )
    else:
        ops = preset_by_id("ops_core")
        if ops and _frame_sets_equal(frame_ids, list(ops["frameIds"])):
            out.extend(
                x
                for x in [
                    _chain_follow_up("ops_then_intel"),
                    _chain_follow_up("ops_then_intel", stack=True),
                ]
                if x is not None
            )
            if not squads_dispatched:
                out.append(DISPATCH_ALL_FOLLOW_UP)
        else:
            intel = preset_by_id("intel")
            if intel and _frame_sets_equal(frame_ids, list(intel["frameIds"])):
                nxt = _chain_follow_up("intel_then_dispatch")
                if nxt:
                    out.append(nxt)
            else:
                full = preset_by_id("full_six")
                if full and _frame_sets_equal(frame_ids, list(full["frameIds"])):
                    nxt = _chain_follow_up("full_six_then_dispatch")
                    if nxt:
                        out.append(nxt)
                    if not squads_dispatched:
                        out.append(DISPATCH_ALL_FOLLOW_UP)

    if queue_depth > 0:
        out.append(_queue_follow_up(queue_depth))
    return out


def chain_playlist_labels(
    chain_label: str,
    preset_labels: list[str],
    dispatch_after: bool = False,
) -> list[str]:
    labels = [f"{chain_label}: {preset}" for preset in preset_labels]
    if dispatch_after:
        labels.append(f"{chain_label}: Dispatch")
    return labels


def resolve_builtin_chain_plan(chain_id: str) -> dict | None:
    chain = chain_by_id(chain_id)
    if not chain:
        return None
    presets = resolve_chain_presets(chain)
    if not presets:
        return None
    return {
        "chainLabel": chain["label"],
        "stages": [{"label": p["label"], "preset": p} for p in presets],
        "dispatchAfter": bool(chain.get("dispatchAfter")),
    }


def labels_for_chain_plan(plan: dict) -> list[str]:
    return chain_playlist_labels(
        plan["chainLabel"],
        [s["label"] for s in plan["stages"]],
        plan.get("dispatchAfter"),
    )


def test_post_run_follow_ups_morning_pulse() -> None:
    morning = preset_by_id("morning_pulse")
    assert morning is not None
    follow_ups = post_run_follow_ups(list(morning["frameIds"]), 0)
    assert len(follow_ups) >= 2
    assert follow_ups[0]["action"]["kind"] == "run_chain"
    assert any(f["action"]["kind"] == "stack_chain" for f in follow_ups)


def test_post_run_follow_ups_retry_on_failure() -> None:
    follow_ups = post_run_follow_ups(["fleet_status"], 1)
    assert len(follow_ups) == 1
    assert follow_ups[0]["action"]["kind"] == "retry_stagger"


def test_post_run_follow_ups_ops_core() -> None:
    ops = preset_by_id("ops_core")
    assert ops is not None
    follow_ups = post_run_follow_ups(list(ops["frameIds"]), 0)
    assert len(follow_ups) == 3
    assert follow_ups[0]["action"]["chainId"] == "ops_then_intel"
    assert any(f["action"]["kind"] == "dispatch_all" for f in follow_ups)


def test_post_run_follow_ups_queue_depth() -> None:
    morning = preset_by_id("morning_pulse")
    assert morning is not None
    follow_ups = post_run_follow_ups(list(morning["frameIds"]), 0, queue_depth=2)
    assert follow_ups[-1]["action"]["kind"] == "run_queue"
    assert "2" in follow_ups[-1]["label"]


def test_post_run_follow_ups_failure_with_queue() -> None:
    follow_ups = post_run_follow_ups(["fleet_status"], 1, queue_depth=3)
    assert len(follow_ups) == 2
    assert follow_ups[1]["action"]["kind"] == "run_queue"


def test_chain_playlist_labels_dispatch() -> None:
    labels = chain_playlist_labels("Full 6 → Dispatch", ["Full six"], True)
    assert len(labels) == 2
    assert "Dispatch" in labels[1]


def test_resolve_builtin_chain_plan_ops_intel() -> None:
    plan = resolve_builtin_chain_plan("ops_then_intel")
    assert plan is not None
    assert len(plan["stages"]) == 2
    labels = labels_for_chain_plan(plan)
    assert "Ops" in labels[0]
    assert "Intel" in labels[1]