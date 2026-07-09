"""Aether portfolio — ventures, bets, and frame routing (config-driven)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from advoi.aether.models import Venture, VentureBet

DEFAULT_PORTFOLIO_PATH = Path(
    os.getenv("AETHER_PORTFOLIO_PATH", "data/aether/portfolio.json")
)


def _parse_bet(raw: dict[str, Any]) -> VentureBet:
    return VentureBet(
        id=str(raw["id"]),
        name=str(raw.get("name", raw["id"])),
        status=raw.get("status", "building"),  # type: ignore[arg-type]
        appetite_days=raw.get("appetite_days"),
        stage=raw.get("stage"),
    )


def _parse_venture(raw: dict[str, Any]) -> Venture:
    bets = tuple(_parse_bet(b) for b in raw.get("bets", []))
    return Venture(
        id=raw["id"],
        name=raw["name"],
        status=raw.get("status", "active"),  # type: ignore[arg-type]
        primary_frames=tuple(raw.get("primary_frames", [])),
        squads=tuple(raw.get("squads", [])),
        repo_path=raw.get("repo_path"),
        bets=bets,
        tags=tuple(raw.get("tags", [])),
    )


def _builtin_ventures() -> tuple[Venture, ...]:
    """Fallback when portfolio.json is missing."""
    return (
        Venture(
            id="advoi-system",
            name="ADVoi System",
            status="active",
            primary_frames=("fleet_status", "systems_pulse", "guardian_status"),
            squads=("platform-squad",),
        ),
        Venture(
            id="firstmate-fleet",
            name="FirstMate Fleet",
            status="active",
            primary_frames=("fleet_status", "open_briefs"),
            squads=("fleet-squad",),
        ),
        Venture(
            id="hermes-beacon",
            name="Hermes Beacon",
            status="active",
            primary_frames=("open_briefs", "memory_health"),
            squads=("briefs-squad",),
        ),
    )


def load_ventures(*, path: Path | None = None) -> tuple[Venture, ...]:
    cfg_path = path or DEFAULT_PORTFOLIO_PATH
    if not cfg_path.is_file():
        return _builtin_ventures()
    try:
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
        return tuple(_parse_venture(v) for v in data.get("ventures", []))
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        return _builtin_ventures()


def _build_maps(ventures: tuple[Venture, ...]) -> tuple[dict[str, Venture], dict[str, str]]:
    by_id = {v.id: v for v in ventures}
    frame_map: dict[str, str] = {}
    for venture in ventures:
        for frame_id in venture.primary_frames:
            if frame_id not in frame_map:
                frame_map[frame_id] = venture.id
    return by_id, frame_map


_VENTURES = load_ventures()
VENTURES: tuple[Venture, ...] = _VENTURES
VENTURES_BY_ID, FRAME_VENTURE_MAP = _build_maps(_VENTURES)


def reload_portfolio(*, path: Path | None = None) -> int:
    """Reload ventures from disk (tests and hot config). Returns venture count."""
    global VENTURES, VENTURES_BY_ID, FRAME_VENTURE_MAP  # noqa: PLW0603
    VENTURES = load_ventures(path=path)
    VENTURES_BY_ID, FRAME_VENTURE_MAP = _build_maps(VENTURES)
    return len(VENTURES)


def venture_for_frame(frame_id: str) -> Venture | None:
    vid = FRAME_VENTURE_MAP.get(frame_id)
    return VENTURES_BY_ID.get(vid) if vid else None


def venture_to_dict(v: Venture) -> dict[str, Any]:
    return {
        "id": v.id,
        "name": v.name,
        "status": v.status,
        "primary_frames": list(v.primary_frames),
        "squads": list(v.squads),
        "repo_path": v.repo_path,
        "tags": list(v.tags),
        "bets": [
            {
                "id": b.id,
                "name": b.name,
                "status": b.status,
                "appetite_days": b.appetite_days,
                "stage": b.stage,
            }
            for b in v.bets
        ],
    }


def portfolio_summary() -> dict[str, Any]:
    return {
        "ventures": [venture_to_dict(v) for v in VENTURES],
        "active_count": sum(1 for v in VENTURES if v.status == "active"),
        "total": len(VENTURES),
        "config_path": str(DEFAULT_PORTFOLIO_PATH),
    }