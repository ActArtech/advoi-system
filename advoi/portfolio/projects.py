"""Project catalog and voice matching for PWA project selector."""

from __future__ import annotations

import re
from typing import Any, Literal

from advoi.aether.gate import load_gate_snapshot
from advoi.aether.portfolio import VENTURES, venture_to_dict
from advoi.decision.frames import FRAMES_BY_ID
from advoi.portfolio.ecr import (
    load_execution_context,
    resolve_execution_target,
    set_session_active_venture,
)

ProjectFunctionKind = Literal["frame", "bet", "custom"]

_SWITCH_RE = re.compile(
    r"\b(?:switch(?:\s+to)?|open|activate|select|change\s+(?:to|project\s+to)|work\s+on)\s+"
    r"([a-z][a-z0-9 _-]+)\b",
    re.IGNORECASE,
)


def _normalize_slug(text: str) -> str:
    return re.sub(r"\s+", "-", (text or "").strip().lower())


def _ecr_fleet_slug_map() -> dict[str, str]:
    ctx = load_execution_context()
    out: dict[str, str] = {}
    ventures = ctx.get("ventures") or []
    if isinstance(ventures, dict):
        for vid, entry in ventures.items():
            if isinstance(entry, dict):
                out[str(vid)] = str(entry.get("fleet_slug") or vid)
        return out
    for entry in ventures:
        if isinstance(entry, dict):
            vid = str(entry.get("venture_id", ""))
            if vid:
                out[vid] = str(entry.get("fleet_slug") or vid)
    return out


def build_project_functions(venture: Any) -> list[dict[str, Any]]:
    functions: list[dict[str, Any]] = []
    for fid in venture.primary_frames:
        frame = FRAMES_BY_ID.get(fid)
        label = frame.label if frame else fid.replace("_", " ").title()
        functions.append(
            {
                "id": fid,
                "label": label,
                "kind": "frame",
                "frame_id": fid,
            }
        )
    for bet in venture.bets:
        functions.append(
            {
                "id": bet.id,
                "label": bet.name,
                "kind": "bet",
                "status": bet.status,
            }
        )
    return functions


def build_projects_catalog() -> dict[str, Any]:
    gate = load_gate_snapshot()
    target = resolve_execution_target(gate_active_slug=gate.active_slug)
    slug_map = _ecr_fleet_slug_map()
    ventures: list[dict[str, Any]] = []
    for venture in VENTURES:
        row = venture_to_dict(venture)
        row["fleet_slug"] = slug_map.get(venture.id)
        row["functions"] = build_project_functions(venture)
        ventures.append(row)
    return {
        "ventures": ventures,
        "active_venture_id": target.get("venture_id"),
        "active_fleet_slug": target.get("fleet_slug"),
        "gate_active_slug": gate.active_slug if gate.found else None,
        "source": target.get("source"),
    }


def match_venture_id(query: str) -> str | None:
    needle = _normalize_slug(query)
    if not needle:
        return None

    for venture in VENTURES:
        candidates = {
            venture.id.lower(),
            venture.name.lower(),
            _normalize_slug(venture.name),
        }
        candidates.update(tag.lower() for tag in venture.tags)
        if needle in candidates:
            return venture.id
        compact = needle.replace("-", "")
        if compact and compact in venture.id.replace("-", ""):
            return venture.id
        if any(needle in candidate or candidate in needle for candidate in candidates):
            return venture.id

    ctx = load_execution_context()
    ventures = ctx.get("ventures") or []
    entries = ventures.values() if isinstance(ventures, dict) else ventures
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        venture_id = str(entry.get("venture_id", ""))
        fleet_slug = str(entry.get("fleet_slug", "")).lower()
        tags = [str(tag).lower() for tag in entry.get("tags", [])]
        if needle in {venture_id.lower(), fleet_slug} or needle in tags:
            return venture_id
    return None


def classify_project_voice_intent(transcript: str) -> dict[str, Any] | None:
    text = (transcript or "").strip().lower()
    if not text:
        return None

    switch_match = _SWITCH_RE.search(text)
    if switch_match:
        venture_id = match_venture_id(switch_match.group(1).strip())
        if venture_id:
            return {"action": "switch_project", "venture_id": venture_id}

    from advoi.fleet.trigger import extract_project_slug
    from advoi.routing.intent import classify_transcript

    slug = extract_project_slug(text)
    if slug:
        venture_id = match_venture_id(slug)
        if venture_id and any(
            phrase in text
            for phrase in (
                "switch",
                "open",
                "activate",
                "select",
                "work on",
                "project",
                "change to",
            )
        ):
            return {"action": "switch_project", "venture_id": venture_id}

    frame_id = classify_transcript(text)
    if frame_id and slug:
        venture_id = match_venture_id(slug)
        if venture_id:
            return {
                "action": "activate_function",
                "venture_id": venture_id,
                "frame_id": frame_id,
            }

    return None


def activate_project(
    venture_id: str,
    *,
    function_id: str | None = None,
) -> dict[str, Any]:
    resolved = match_venture_id(venture_id) or venture_id.strip()
    venture = next((v for v in VENTURES if v.id == resolved), None)
    if venture is None:
        return {"ok": False, "error": f"Unknown venture: {venture_id}"}

    target = set_session_active_venture(resolved)
    return {
        "ok": True,
        "venture_id": resolved,
        "venture_name": venture.name,
        "fleet_slug": target.get("fleet_slug"),
        "function_id": function_id,
        "frame_id": function_id if function_id in FRAMES_BY_ID else None,
    }


def spoken_project_switch(venture_id: str, *, function_id: str | None = None) -> str:
    venture = next((v for v in VENTURES if v.id == venture_id), None)
    name = venture.name if venture else venture_id
    if function_id and function_id in FRAMES_BY_ID:
        frame = FRAMES_BY_ID[function_id]
        return f"Switched to {name} and queued {frame.label}."
    return f"Switched to {name}. Frames and squads are scoped to this project."