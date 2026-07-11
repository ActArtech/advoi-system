"""Unit tests for agent slice models (mirrors web/lib/agents/agentSlices.ts)."""

from __future__ import annotations

import re
import time

FRAME_SHORT = {
    "fleet_status": "fleet",
    "open_briefs": "briefs",
    "queue_deep_review": "review",
    "systems_pulse": "pulse",
    "memory_health": "memory",
    "guardian_status": "guardian",
}

DEFAULT_SIX = [
    "fleet_status",
    "open_briefs",
    "queue_deep_review",
    "systems_pulse",
    "memory_health",
    "guardian_status",
]

SLICE_PRESETS = [
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
        "frameIds": list(DEFAULT_SIX),
        "mode": "parallel",
    },
]


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


PRESET_CHAINS = [
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
        "id": "full_six_then_dispatch",
        "label": "Full 6 → Dispatch",
        "presetIds": ["full_six"],
        "dispatchAfter": True,
    },
]

MAX_USER_PRESETS = 8


def preset_by_id(preset_id: str) -> dict | None:
    return next((p for p in SLICE_PRESETS if p["id"] == preset_id), None)


def chain_by_id(chain_id: str) -> dict | None:
    return next((c for c in PRESET_CHAINS if c["id"] == chain_id), None)


def resolve_chain_presets(chain: dict) -> list[dict]:
    return [p for pid in chain["presetIds"] if (p := preset_by_id(pid)) is not None]


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


def wave_size_for_mode(mode: str) -> int:
    if mode == "parallel":
        return 64
    if mode == "wave":
        return 2
    return 1


def chunk_frame_waves(frame_ids: list[str], mode: str) -> list[list[str]]:
    size = wave_size_for_mode(mode)
    if not frame_ids:
        return []
    if mode == "parallel":
        return [frame_ids]
    waves: list[list[str]] = []
    for i in range(0, len(frame_ids), size):
        waves.append(frame_ids[i : i + size])
    return waves


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


def describe_wave_plan(frame_ids: list[str], mode: str) -> dict:
    waves = chunk_frame_waves(frame_ids, mode)
    return {
        "mode": mode,
        "waveCount": len(waves),
        "waves": [
            {
                "index": i,
                "frameIds": wave,
                "labels": [short_frame_label(fid) for fid in wave],
            }
            for i, wave in enumerate(waves)
        ],
    }


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