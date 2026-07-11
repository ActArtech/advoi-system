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
    results: list[dict] | None = None,
) -> list[dict]:
    selected_ids = selected_ids or set()
    running_frame_ids = running_frame_ids or set()
    results = results or []
    frame_by_agent = {f["agent_id"]: f for f in frames}
    result_by_frame = {r["frame_id"]: r for r in results}
    out = []
    for agent in agents:
        frame = frame_by_agent.get(agent["id"]) or {}
        frame_id = frame.get("id") or agent.get("frame_id") or agent["id"]
        result = result_by_frame.get(frame_id)
        phase = "idle"
        if frame_id in running_frame_ids:
            phase = "running"
        elif result:
            phase = "error" if result.get("status") == "error" else "ok"
        out.append(
            {
                "agentId": agent["id"],
                "frameId": frame_id,
                "label": frame.get("label") or agent.get("name") or agent["id"],
                "shortLabel": short_frame_label(frame_id),
                "warm": bool(agent.get("cached")),
                "phase": phase,
                "selected": agent["id"] in selected_ids,
            }
        )
    return out


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