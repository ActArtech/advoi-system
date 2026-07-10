"""Parse fm-aether-gate markdown into gate_snapshot PEL payloads."""

from __future__ import annotations

import re
from typing import Any

_PASS_EXIT_CODES = {0, 1}
_HEADER_TS_RE = re.compile(r"^#\s+Aether output gate\s+—\s+(.+)$", re.MULTILINE)
_ACTIONABLE_RE = re.compile(r"actionable=(\d+)", re.IGNORECASE)


def _field_value(line: str, label: str) -> str | None:
    clean = re.sub(r"\*+", "", line).strip()
    prefix = f"{label}:"
    if not clean.lower().startswith(prefix.lower()):
        return None
    value = clean.split(":", 1)[1].strip().strip("`\"'")
    return value or None


def _parse_checks_table(text: str) -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []
    in_checks = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "## Checks":
            in_checks = True
            continue
        if in_checks and stripped.startswith("## "):
            break
        if not in_checks or not stripped.startswith("|"):
            continue
        if "Check" in stripped and "OK" in stripped:
            continue
        if re.match(r"^\|[-:| ]+\|$", stripped):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 3:
            continue
        checks.append({"name": cells[0], "ok": cells[1], "detail": cells[2]})
    return checks


def _parse_actionable_count(text: str, checks: list[dict[str, str]]) -> int:
    for check in checks:
        if check.get("name") == "findings_present":
            match = _ACTIONABLE_RE.search(check.get("detail", ""))
            if match:
                return int(match.group(1))
    section = "## Actionable findings"
    if section not in text:
        return 0
    tail = text.split(section, 1)[1]
    count = 0
    for line in tail.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            break
        if stripped.startswith("- "):
            count += 1
    return count


def parse_gate_report(
    text: str,
    *,
    exit_code: int,
    report_path: str,
) -> dict[str, Any] | None:
    """Parse fm-aether-gate markdown into a gate_snapshot payload."""
    if exit_code not in _PASS_EXIT_CODES:
        return None

    timestamp: str | None = None
    match = _HEADER_TS_RE.search(text)
    if match:
        timestamp = match.group(1).strip()

    verdict: str | None = None
    slug: str | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if verdict is None:
            verdict = _field_value(stripped, "Verdict")
        if slug is None:
            slug = _field_value(stripped, "Active slug")
        if verdict and slug:
            break

    checks = _parse_checks_table(text)
    actionable_count = _parse_actionable_count(text, checks)

    return {
        "verdict": verdict,
        "slug": slug,
        "exit_code": exit_code,
        "actionable_count": actionable_count,
        "report_path": report_path,
        "timestamp": timestamp,
        "checks": checks,
    }


async def emit_gate_snapshot_from_report(report_path: str, exit_code: int) -> bool:
    from pathlib import Path

    from advoi.portfolio.pel import append_portfolio_event

    path = Path(report_path)
    text = path.read_text(encoding="utf-8")
    payload = parse_gate_report(text, exit_code=exit_code, report_path=str(path))
    if payload is None:
        return False
    venture_slug = payload.get("slug")
    return await append_portfolio_event("gate_snapshot", payload, venture_slug=venture_slug)