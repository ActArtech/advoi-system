"""Unit tests for agent slice models (mirrors web/lib/agents/agentSlices.ts)."""

from __future__ import annotations

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


def short_frame_label(frame_id: str) -> str:
    return FRAME_SHORT.get(frame_id, frame_id.replace("_", " ")[:8])


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
                phase = "error" if status == "error" else "ok"

        last_run = agent.get("last_run") or {}
        out.append(
            {
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
        )
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