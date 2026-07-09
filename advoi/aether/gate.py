"""Aether gate — read portfolio governance verdict from FirstMate fleet tree."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from advoi.aether.models import GateSnapshot, GateVerdict

_VERDICT_MAP: dict[str, GateVerdict] = {
    "pass": "pass",
    "hold": "hold",
    "fail": "fail",
    "blocked": "fail",
    "go": "pass",
    "no-go": "fail",
    "no go": "fail",
}


def _fleet_root() -> Path:
    return Path(os.getenv("FIRSTMATE_FLEET_PATH", "/opt/firstmate-fleet"))


def _read_text(path: Path, *, max_bytes: int = 8_192) -> str | None:
    try:
        data = path.read_bytes()
        if not data:
            return ""
        return data[:max_bytes].decode("utf-8", errors="replace")
    except OSError:
        return None


def _normalize_verdict(raw: str | None) -> GateVerdict:
    if not raw:
        return "unknown"
    key = raw.strip().lower().replace("_", "-")
    for token, verdict in _VERDICT_MAP.items():
        if token in key:
            return verdict
    return "unknown"


def _strip_markdown_field(line: str) -> str:
    return re.sub(r"\*+", "", line).strip()


def _field_value(line: str, label: str) -> str | None:
    clean = _strip_markdown_field(line)
    prefix = f"{label}:"
    if not clean.lower().startswith(prefix.lower()):
        return None
    value = clean.split(":", 1)[1].strip().strip("`\"'")
    return value or None


def parse_gate_markdown(text: str) -> GateSnapshot:
    verdict_raw: str | None = None
    active_slug: str | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if verdict_raw is None:
            verdict_raw = _field_value(stripped, "Verdict")
        if active_slug is None:
            for label in ("Active slug", "Active project", "Active"):
                active_slug = _field_value(stripped, label)
                if active_slug:
                    break
    return GateSnapshot(
        found=True,
        verdict=_normalize_verdict(verdict_raw),
        active_slug=active_slug,
        raw_preview=text[:400],
    )


def load_gate_snapshot(*, fleet_root: Path | None = None) -> GateSnapshot:
    root = fleet_root or _fleet_root()
    gate_path = root / "aether-gate-latest.md"
    text = _read_text(gate_path)
    if text is None:
        return GateSnapshot(found=False, path=str(gate_path))
    snap = parse_gate_markdown(text)
    snap.path = str(gate_path)
    return snap


def gate_dict_for_fleet_detail() -> dict[str, Any]:
    """Legacy shape used by fleet snapshot detail."""
    snap = load_gate_snapshot()
    if not snap.found:
        return {"aether_found": False}
    return {
        "aether_found": True,
        "verdict": snap.verdict if snap.verdict != "unknown" else None,
        "active_slug": snap.active_slug,
    }