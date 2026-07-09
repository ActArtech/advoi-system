"""Aether domain models — ventures, bets, gate verdicts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

VentureStatus = Literal["active", "hibernate", "archived", "idea"]
BetStatus = Literal["shaped", "building", "validating", "shipped", "paused"]
GateVerdict = Literal["pass", "hold", "fail", "unknown"]


@dataclass(frozen=True)
class VentureBet:
    """Shaped bet within a venture (maps to .aether/BET.md pattern)."""

    id: str
    name: str
    status: BetStatus
    appetite_days: int | None = None
    stage: str | None = None


@dataclass(frozen=True)
class Venture:
    id: str
    name: str
    status: VentureStatus
    primary_frames: tuple[str, ...]
    squads: tuple[str, ...]
    repo_path: str | None = None
    bets: tuple[VentureBet, ...] = ()
    tags: tuple[str, ...] = ()


@dataclass
class GateSnapshot:
    found: bool
    verdict: GateVerdict = "unknown"
    active_slug: str | None = None
    raw_preview: str = ""
    path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "found": self.found,
            "verdict": self.verdict,
            "active_slug": self.active_slug,
            "raw_preview": self.raw_preview[:400],
            "path": self.path,
        }


@dataclass
class PortfolioContext:
    """Bundle for voice prompts and frame enrichment."""

    ventures: list[dict[str, Any]] = field(default_factory=list)
    active_count: int = 0
    gate: GateSnapshot | None = None
    frame_routes: dict[str, list[str]] = field(default_factory=dict)

    def prompt_block(self, *, max_ventures: int = 4) -> str:
        lines: list[str] = []
        if self.gate and self.gate.found and self.gate.verdict != "unknown":
            lines.append(f"Aether gate: {self.gate.verdict}.")
        for v in self.ventures[:max_ventures]:
            bets = ", ".join(b["name"] for b in v.get("bets", [])[:2])
            extra = f" Bets: {bets}." if bets else ""
            lines.append(f"- {v['name']} ({v['status']}){extra}")
        return "\n".join(lines) if lines else ""