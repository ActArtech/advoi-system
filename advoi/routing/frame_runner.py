"""Execute decision frames via specialist agents."""

from __future__ import annotations

import asyncio
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from advoi.cache.agent_cache import read_agent_cache
from advoi.copy_style import format_briefs_spoken, normalize_brief_title, plain_copy
from advoi.decision.frames import DecisionFrame, get_frame
from advoi.memory import MemoryRouter
from advoi.routing.agents import AGENTS
from advoi.routing.diagnostic_frames import run_guardian_status, run_memory_health
from advoi.routing.orchestrator import run_systems_pulse



@dataclass
class FrameResult:
    frame_id: str
    agent_id: str
    status: str
    spoken_summary: str
    detail: dict[str, Any]


def _fleet_root() -> Path:
    return Path(os.getenv("FIRSTMATE_FLEET_PATH", "/opt/firstmate-fleet"))


def _read_text(path: Path, *, max_bytes: int = 120_000) -> str | None:
    try:
        data = path.read_bytes()
        if not data:
            return ""
        return data[:max_bytes].decode("utf-8", errors="replace")
    except OSError:
        return None


def _parse_profile_field(text: str, field: str) -> str | None:
    for line in text.splitlines():
        if line.startswith(f"{field}:"):
            value = line.split(":", 1)[1].strip().strip("\"'")
            return value or None
    return None


def _parse_backlog_items(section_text: str) -> list[str]:
    items: list[str] = []
    for line in section_text.splitlines():
        stripped = line.strip()
        if stripped in {"_(none)_", "(none)"}:
            continue
        match = re.match(r"^- \[[ xX]\] \*\*([^*]+)\*\*", stripped)
        if match:
            items.append(match.group(1))
        elif stripped.startswith("- [ ]") or stripped.startswith("- [x]"):
            items.append(stripped.lstrip("- ").strip()[:80])
    return items


def _extract_markdown_section(text: str, heading: str) -> str:
    pattern = re.compile(
        rf"^## {re.escape(heading)}\s*$",
        re.IGNORECASE | re.MULTILINE,
    )
    match = pattern.search(text)
    if not match:
        return ""
    start = match.end()
    next_heading = re.search(r"^## ", text[start:], re.MULTILINE)
    end = start + next_heading.start() if next_heading else len(text)
    return text[start:end]


def _file_age_seconds(path: Path) -> float | None:
    try:
        return max(0.0, time.time() - path.stat().st_mtime)
    except OSError:
        return None


def _read_state_flag(path: Path) -> str | None:
    text = _read_text(path, max_bytes=256)
    if text is None:
        return None
    return text.strip() or None


def _fleet_profile_snapshot(data_dir: Path) -> dict[str, Any]:
    profile_path = data_dir / "config" / "fleet-profile.md"
    text = _read_text(profile_path)
    if text is None:
        return {"profile_found": False}
    return {
        "profile_found": True,
        "active_slug": _parse_profile_field(text, "active_slug"),
        "github_repo": _parse_profile_field(text, "github_repo"),
        "mode": _parse_profile_field(text, "mode"),
    }


def _fleet_backlog_snapshot(data_dir: Path, active_slug: str | None) -> dict[str, Any]:
    backlog_path = data_dir / "backlog.md"
    text = _read_text(backlog_path)
    if text is None:
        return {"backlog_found": False}

    in_flight = _parse_backlog_items(_extract_markdown_section(text, "In flight"))
    queued = _parse_backlog_items(_extract_markdown_section(text, "Queued"))
    blocked = _parse_backlog_items(_extract_markdown_section(text, "Blocked"))

    snapshot_line = ""
    for line in text.splitlines():
        if line.startswith(">") and "Staging:" in line:
            snapshot_line = line.lstrip("> ").strip()
            break

    return {
        "backlog_found": True,
        "active_slug": active_slug,
        "in_flight": in_flight,
        "queued": queued,
        "blocked": blocked,
        "snapshot_line": snapshot_line,
    }


def _fleet_state_snapshot(state_dir: Path) -> dict[str, Any]:
    afk_raw = _read_state_flag(state_dir / ".afk")
    afk_on = afk_raw is not None
    wake_queue_bytes = 0
    wake_path = state_dir / ".wake-queue"
    try:
        wake_queue_bytes = wake_path.stat().st_size if wake_path.is_file() else 0
    except OSError:
        wake_queue_bytes = 0

    guard_beat_age = _file_age_seconds(state_dir / ".captain-guard-beat")
    guard_pid_present = (state_dir / ".captain-guard.pid").is_file()
    supervise_pid_present = (state_dir / ".supervise-daemon.pid").is_file()

    return {
        "state_found": state_dir.is_dir(),
        "afk_on": afk_on,
        "wake_queue_bytes": wake_queue_bytes,
        "guard_beat_age_secs": guard_beat_age,
        "guard_pid_present": guard_pid_present,
        "supervise_pid_present": supervise_pid_present,
    }


def _aether_snapshot(data_dir: Path) -> dict[str, Any]:
    from advoi.aether.gate import load_gate_snapshot

    snap = load_gate_snapshot(fleet_root=data_dir)
    if not snap.found:
        return {"aether_found": False}
    return {
        "aether_found": True,
        "verdict": snap.verdict if snap.verdict != "unknown" else None,
        "active_slug": snap.active_slug,
    }


def _summarize_fleet_snapshot(
    profile: dict[str, Any],
    backlog: dict[str, Any],
    state: dict[str, Any],
    advanced_text: str | None,
    aether: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    active = profile.get("active_slug") or backlog.get("active_slug") or "unknown"
    parts: list[str] = [f"Fleet snapshot for {active}."]

    if state.get("afk_on"):
        parts.append("Continuous AFK loop is on.")
    else:
        parts.append("AFK loop looks off.")

    in_flight = backlog.get("in_flight") or []
    queued = backlog.get("queued") or []
    if in_flight:
        parts.append(
            f"{len(in_flight)} in flight: {', '.join(in_flight[:2])}."
        )
    else:
        parts.append("Nothing in flight.")

    if queued:
        parts.append(f"{len(queued)} queued; next up {queued[0]}.")
    else:
        parts.append("Queue is empty.")

    wake_bytes = int(state.get("wake_queue_bytes") or 0)
    if wake_bytes > 0:
        parts.append(f"Wake queue has {wake_bytes} bytes pending.")

    if advanced_text:
        adv_lines = [
            line.strip()
            for line in advanced_text.splitlines()
            if line.strip() and not line.startswith("###")
        ]
        if adv_lines:
            parts.append(adv_lines[0].replace("**", "").replace("&lt;", "<"))

    if aether.get("verdict"):
        parts.append(f"Aether gate {aether['verdict']}.")

    spoken = " ".join(parts)
    detail = {
        "source": "file_snapshot",
        "active_slug": active,
        "profile": profile,
        "backlog": {
            "in_flight": in_flight,
            "queued_count": len(queued),
            "queued_full": queued,
            "queued_preview": queued[:5],
            "blocked_count": len(backlog.get("blocked") or []),
            "snapshot_line": backlog.get("snapshot_line"),
        },
        "state": state,
        "aether": aether,
        "advanced_preview": (advanced_text or "")[:400],
    }
    return spoken, detail


async def _run_readonly_fleet_script(script: Path, *, env: dict[str, str]) -> str | None:
    if not script.is_file():
        return None
    proc = await asyncio.create_subprocess_exec(
        "bash",
        str(script),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={**os.environ, **env},
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=20)
    text = (stdout or stderr).decode("utf-8", errors="replace").strip()
    if proc.returncode != 0 and not text:
        return None
    return text


def _collect_fleet_snapshot_from_disk(root: Path) -> tuple[str, dict[str, Any]] | None:
    data_dir = root / "data"
    state_dir = root / "state"
    if not data_dir.is_dir():
        return None

    profile = _fleet_profile_snapshot(data_dir)
    active_slug = profile.get("active_slug")
    backlog = _fleet_backlog_snapshot(data_dir, active_slug)
    state = _fleet_state_snapshot(state_dir)
    aether = _aether_snapshot(data_dir)

    if not profile.get("profile_found") and not backlog.get("backlog_found"):
        return None

    spoken, detail = _summarize_fleet_snapshot(
        profile,
        backlog,
        state,
        advanced_text=None,
        aether=aether,
    )
    detail["snapshot_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return spoken, detail


async def _run_fleet_scout() -> tuple[str, dict[str, Any], str]:
    """Return spoken summary, detail dict, and frame status."""
    if os.getenv("ADVOI_FRAME_MOCK", "").lower() in {"1", "true", "yes"}:
        return (
            "Fleet mock: Hermes and FirstMate runners look healthy. Two projects idle.",
            {"mode": "mock", "projects_idle": 2},
            "ok",
        )

    root = _fleet_root()
    data_dir = root / "data"
    state_dir = root / "state"
    script_env = {
        "FM_DATA_OVERRIDE": str(data_dir),
        "FM_STATE_OVERRIDE": str(state_dir),
        "FM_FLEET_PROFILE": str(data_dir / "config" / "fleet-profile.md"),
    }

    disk_snapshot = _collect_fleet_snapshot_from_disk(root)
    if disk_snapshot is None:
        return (
            "Fleet bridge is not configured on this host yet.",
            {"error": "missing_fleet_data", "fleet_root": str(root)},
            "error",
        )

    spoken, detail = disk_snapshot
    backlog_full = {
        "backlog_found": True,
        "active_slug": detail.get("active_slug"),
        "in_flight": detail["backlog"]["in_flight"],
        "queued": detail["backlog"].get("queued_full") or detail["backlog"]["queued_preview"],
        "blocked": [],
        "snapshot_line": detail["backlog"].get("snapshot_line"),
    }
    advanced_script = root / "scripts" / "fm-advanced-status.sh"
    try:
        advanced_text = await _run_readonly_fleet_script(advanced_script, env=script_env)
        if advanced_text:
            spoken, refreshed = _summarize_fleet_snapshot(
                detail["profile"],
                backlog_full,
                detail["state"],
                advanced_text,
                detail["aether"],
            )
            detail.update(refreshed)
            detail["advanced_preview"] = advanced_text[:400]
    except (asyncio.TimeoutError, FileNotFoundError):
        detail["advanced_error"] = "timeout_or_missing"

    if "ERROR:" in spoken or "container" in spoken.lower() and "not running" in spoken.lower():
        return spoken, detail, "error"
    return spoken, detail, "ok"


def _voice_trim(text: str, *, max_sentences: int = 4) -> str:
    parts = [p.strip() for p in text.replace("\n", " ").split(". ") if p.strip()]
    spoken = ". ".join(parts[:max_sentences])
    if spoken and not spoken.endswith("."):
        spoken += "."
    return spoken or text[:400]


def _normalize_brief_list(titles: list[str]) -> list[str]:
    """Dedupe and normalize brief titles (single source list only — never multi-store merge)."""
    seen: set[str] = set()
    out: list[str] = []
    for title in titles:
        clean = normalize_brief_title(title)[:120]
        key = clean.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(clean)
    return out


async def _load_open_briefs() -> tuple[list[str], str]:
    """Load open briefs: Postgres canonical → fill Redis cache; Redis only if PG down.

    Read order (ADR-026 ship #2b):
      1. Postgres ``decision_briefs`` (canonical)
      2. On PG hit: fill Redis ``advoi:briefs:open`` (cache only)
      3. On PG miss/unavailable: degraded Redis cache, then caller may Hindsight-enrich
    Redis is never merged with PG as a second title source.
    """
    from advoi.memory.briefs_cache import (
        fill_open_briefs_cache,
        invalidate_open_briefs_cache,
        read_open_briefs_cache,
    )
    from advoi.memory.postgres_store import list_open_briefs

    pg = await list_open_briefs()
    if pg is not None:
        items = _normalize_brief_list(pg)
        if items:
            fill_open_briefs_cache(items)
            return items, "postgres"
        # Canonical empty — drop stale cache so spoken output cannot resurrect deleted briefs.
        invalidate_open_briefs_cache()
        return [], "postgres"

    # Postgres unavailable: serve last filled cache only (not a merge path).
    cached = _normalize_brief_list(read_open_briefs_cache())
    if cached:
        return cached, "redis_cache"
    return [], "unavailable"


async def _run_brief_curator() -> tuple[str, dict[str, Any]]:
    if os.getenv("ADVOI_FRAME_MOCK", "").lower() in {"1", "true", "yes"}:
        mock = ["ADVoi voice launch", "Staging catch-up"]
        return format_briefs_spoken(mock), {"mode": "mock", "briefs": mock}

    items, source = await _load_open_briefs()
    # Optional Hindsight enrich when Postgres (and degraded cache) are empty —
    # not a third merge source alongside PG/Redis titles.
    if not items:
        router = MemoryRouter()
        recall = await router.recall(
            session_id="voice-main",
            query="open decision brief ADVoi portfolio staging",
        )
        enrich: list[str] = []
        for bucket in (recall.strategic, recall.operational, recall.ephemeral):
            for item in bucket[:3]:
                text = item.get("text") or item.get("summary") or item.get("content")
                if text:
                    enrich.append(str(text)[:120])
        items = _normalize_brief_list(enrich)
        if items:
            source = "hindsight_enrich"
    if items:
        return format_briefs_spoken(items), {"briefs": items, "source": source}
    return (
        "No briefs in memory yet. Say what you want captured and I'll log it after confirm.",
        {"briefs": [], "source": source},
    )


async def _run_review_queue(*, confirmed: bool) -> tuple[str, dict[str, Any]]:
    from advoi.guardian.confirmation import evaluate_frame_confirmation
    from advoi.memory.review_queue import desktop_brief_url, enqueue_review

    gate = evaluate_frame_confirmation("queue_deep_review", confirmed=confirmed)
    if not gate["proceed"]:
        return (
            str(gate.get("prompt") or "To queue a deep review, confirm yes on voice or tap again."),
            {"awaiting_confirmation": True},
        )

    title = "ADVoi voice validation"
    briefs, _ = await _load_open_briefs()
    if briefs:
        title = briefs[0]

    if os.getenv("ADVOI_FRAME_MOCK", "").lower() in {"1", "true", "yes"}:
        mock_id = 0
        url = desktop_brief_url(mock_id)
        return (
            f"Queued deep review for {title}. Desktop brief: {url}.",
            {"mode": "mock", "queued": True, "queue_id": mock_id, "title": title, "brief_url": url},
        )

    queue_id = await enqueue_review(
        title,
        source_frame="queue_deep_review",
        metadata={"trigger": "voice_frame"},
    )
    if queue_id is None:
        return (
            "Deep review queued for desktop prep. I'll surface the brief when it's ready.",
            {"queued": True, "persistence": "unavailable", "title": title},
        )

    url = desktop_brief_url(queue_id)
    return (
        f"Queued deep review for {title}. Desktop brief: {url}.",
        {"queued": True, "queue_id": queue_id, "title": title, "brief_url": url},
    )


def _cached_frame(agent_id: str) -> FrameResult | None:
    try:
        data = read_agent_cache(agent_id)
        if not data:
            return None
        spoken = plain_copy(data.get("spoken_summary", ""))
        if _looks_like_fleet_error(spoken):
            return None
        return FrameResult(
            frame_id=data["frame_id"],
            agent_id=data["agent_id"],
            status=data["status"],
            spoken_summary=spoken,
            detail={"cached": True},
        )
    except Exception:
        return None


def _looks_like_fleet_error(text: str) -> bool:
    lowered = text.lower()
    return (
        "error:" in lowered
        or "container firstmate-fleet not running" in lowered
        or "fleet bridge is not configured" in lowered
        or "timed out" in lowered
    )


def _frame_guardian_status(status: str, *, confirmed: bool) -> str:
    if status == "confirmation_required":
        return "pending"
    if confirmed:
        return "allowed"
    return "not_required"


async def _emit_frame_run_event(
    result: FrameResult,
    *,
    confirmed: bool,
    refresh: bool,
    source: str = "api",
) -> None:
    """Append PEL row for a completed frame run (best-effort)."""
    from advoi.analytics.pel import EventSource, EventType, safe_append_event

    detail = result.detail or {}
    venture = (
        str(detail.get("active_slug") or detail.get("venture_id") or detail.get("project") or "advoi")
    )
    detail_keys = sorted(str(k) for k in detail.keys())[:24]
    await safe_append_event(
        venture_id=venture,
        source=EventSource.API if source == "api" else source,
        event_type=EventType.FRAME_RUN,
        payload={
            "frame_id": result.frame_id,
            "agent_id": result.agent_id,
            "status": result.status,
            "spoken_summary_len": len(result.spoken_summary or ""),
            "confirmed": confirmed,
            "refresh": refresh,
            "detail_keys": detail_keys,
            "cached": bool(detail.get("cached")),
        },
        guardian_status=_frame_guardian_status(result.status, confirmed=confirmed),
        execution_ref=(
            str(detail["queue_id"])
            if detail.get("queue_id") is not None
            else None
        ),
    )


async def run_frame(
    frame_id: str,
    *,
    confirmed: bool = False,
    use_cache: bool = True,
    refresh: bool = False,
) -> FrameResult:
    frame = get_frame(frame_id)
    if not frame:
        raise ValueError(f"Unknown frame: {frame_id}")

    agent = AGENTS.get(frame.agent_id)
    if not agent:
        raise ValueError(f"Unknown agent for frame: {frame_id}")

    bypass_cache = refresh or confirmed
    if use_cache and not bypass_cache:
        cached = _cached_frame(frame.agent_id)
        if cached and cached.status == "ok":
            await _emit_frame_run_event(cached, confirmed=confirmed, refresh=refresh)
            return cached

    if frame.id == "fleet_status":
        spoken, detail, status = await _run_fleet_scout()
        spoken = _voice_trim(spoken)
    elif frame.id == "open_briefs":
        spoken, detail = await _run_brief_curator()
        status = "ok"
    elif frame.id == "queue_deep_review":
        spoken, detail = await _run_review_queue(confirmed=confirmed)
        status = "confirmation_required" if detail.get("awaiting_confirmation") else "ok"
    elif frame.id == "systems_pulse":
        result = await run_systems_pulse(refresh=refresh)
        from advoi.aether.architect import post_frame_aether

        await post_frame_aether(result)
        await _emit_frame_run_event(result, confirmed=confirmed, refresh=refresh)
        return result
    elif frame.id == "memory_health":
        spoken, detail, status = await run_memory_health()
    elif frame.id == "guardian_status":
        spoken, detail, status = await run_guardian_status()
    else:
        spoken, detail = "That frame is not wired yet.", {}
        status = "unsupported"

    if frame.id == "open_briefs":
        full_spoken = plain_copy(spoken)
    else:
        preamble = agent.speaks_first
        full_spoken = plain_copy(f"{preamble} {spoken}".strip())

    result = FrameResult(
        frame_id=frame.id,
        agent_id=agent.id,
        status=status,
        spoken_summary=full_spoken,
        detail=detail,
    )
    from advoi.aether.architect import post_frame_aether

    await post_frame_aether(result)
    await _emit_frame_run_event(result, confirmed=confirmed, refresh=refresh)
    return result


def frame_to_dict(frame: DecisionFrame) -> dict[str, Any]:
    agent = AGENTS[frame.agent_id]
    return {
        "id": frame.id,
        "label": frame.label,
        "agent_id": frame.agent_id,
        "agent_name": agent.name,
        "requires_confirmation": frame.requires_confirmation,
        "voice_prompt": frame.voice_prompt,
    }