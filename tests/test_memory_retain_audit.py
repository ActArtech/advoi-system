"""ADR-026 retain integrity audit — static guards (advoi-memory-retain-audit-01).

Forbids:
- Direct Hindsight retain outside the router → hindsight implementation stack
- Free-form retain_operational_unified outside memory package / tests
- Fleet-backlog text in strategic (Hindsight-bound) retain payloads
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from advoi.memory.write_targets import EVENT_WRITE_MAP, MemoryEventType, WriteTarget, targets_for

ROOT = Path(__file__).resolve().parents[1]
ADVOI_PKG = ROOT / "advoi"

# Production packages that may call Hindsight retain primitives.
_HINDSIGHT_ALLOWED = {
    "advoi/memory/hindsight.py",
    "advoi/memory/router.py",
    "advoi/memory/bridge_server.py",
}

# retain_operational_unified may only be imported by the router (and tests/memory package).
_OPERATIONAL_RETAIN_ALLOWED_PREFIXES = (
    "advoi/memory/",
    "tests/",
)

# Patterns that must not appear in strategic retain payload construction.
_FLEET_BACKLOG_PATTERNS = (
    re.compile(r"run_next_backlog", re.I),
    re.compile(r"fleet[_\s-]*backlog", re.I),
    re.compile(r"FIRSTMATE_FLEET_PATH", re.I),
)


def _rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _iter_py(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_event_write_map_covers_all_event_types():
    """Every MemoryEventType must have an explicit write target tuple."""
    missing = [e for e in MemoryEventType if e not in EVENT_WRITE_MAP]
    assert missing == [], f"EVENT_WRITE_MAP missing: {missing}"


def test_squad_lesson_never_writes_hindsight():
    assert WriteTarget.HINDSIGHT not in targets_for(MemoryEventType.SQUAD_LESSON)


def test_decision_brief_never_writes_hindsight():
    """Briefs are Postgres canonical; Hindsight seed is flagged, not app retain."""
    assert WriteTarget.HINDSIGHT not in targets_for(MemoryEventType.DECISION_BRIEF)
    assert targets_for(MemoryEventType.DECISION_BRIEF) == (WriteTarget.POSTGRES,)


def test_no_direct_retain_strategic_outside_allowed():
    """Application code must not import retain_strategic except via MemoryRouter stack."""
    offenders: list[str] = []
    for path in _iter_py(ADVOI_PKG):
        rel = _rel(path)
        if rel in _HINDSIGHT_ALLOWED:
            continue
        src = _read(path)
        if re.search(r"from\s+advoi\.memory\.hindsight\s+import\s+.*retain_strategic", src):
            offenders.append(rel)
        if (
            re.search(r"import\s+advoi\.memory\.hindsight\s+as\s+\w+", src)
            and "retain_strategic" in src
        ):
            # only flag if retain_strategic is referenced
            if "retain_strategic" in src and rel not in _HINDSIGHT_ALLOWED:
                offenders.append(rel)
    assert offenders == [], f"direct retain_strategic import: {offenders}"


def test_no_aretain_outside_hindsight_implementation():
    """client.aretain must stay inside hindsight.py (and bridge scripts, not in advoi/)."""
    offenders: list[str] = []
    for path in _iter_py(ADVOI_PKG):
        rel = _rel(path)
        if rel in {"advoi/memory/hindsight.py"}:
            continue
        src = _read(path)
        if ".aretain(" in src or "aretain(" in src:
            offenders.append(rel)
    assert offenders == [], f"direct aretain outside hindsight.py: {offenders}"


def test_no_retain_operational_unified_outside_memory_package():
    """Operational retains must go through MemoryRouter (not free-form event strings)."""
    offenders: list[str] = []
    for path in _iter_py(ADVOI_PKG):
        rel = _rel(path)
        if any(rel.startswith(p) for p in _OPERATIONAL_RETAIN_ALLOWED_PREFIXES):
            continue
        src = _read(path)
        if "retain_operational_unified" in src:
            offenders.append(rel)
    assert offenders == [], f"retain_operational_unified bypass: {offenders}"


def test_production_router_retain_uses_memory_event_type():
    """Every MemoryRouter().retain / router.retain in advoi/ must pass MemoryEventType.*."""
    call_re = re.compile(
        r"(?:MemoryRouter\(\)\s*\.\s*retain|router\s*\.\s*retain)\s*\(\s*([^,\n]+)",
        re.M,
    )
    offenders: list[str] = []
    for path in _iter_py(ADVOI_PKG):
        src = _read(path)
        for match in call_re.finditer(src):
            first_arg = match.group(1).strip()
            if not first_arg.startswith("MemoryEventType."):
                offenders.append(f"{_rel(path)}: first arg {first_arg!r}")
    assert offenders == [], f"retain without MemoryEventType: {offenders}"


def test_strategic_retain_payloads_have_no_fleet_backlog_text():
    """Call sites that retain strategic MemoryEventTypes must not embed backlog dumps."""
    strategic_markers = (
        "MemoryEventType.VENTURE_BELIEF_UPDATE",
        "MemoryEventType.PORTFOLIO_FACT",
        "MemoryEventType.GOVERNANCE_DECISION",
        "MemoryEventType.CROSS_PROJECT_SYNTHESIS",
    )
    offenders: list[str] = []
    for path in _iter_py(ADVOI_PKG):
        rel = _rel(path)
        if rel.startswith("advoi/memory/"):
            continue  # implementation may mention fleet only as env/docs
        src = _read(path)
        if not any(m in src for m in strategic_markers):
            continue
        for pat in _FLEET_BACKLOG_PATTERNS:
            if pat.search(src):
                offenders.append(f"{rel} matches {pat.pattern}")
    assert offenders == [], f"fleet backlog near strategic retain: {offenders}"


def test_hindsight_targets_only_strategic_event_types():
    strategic = {
        MemoryEventType.PORTFOLIO_FACT,
        MemoryEventType.GOVERNANCE_DECISION,
        MemoryEventType.CROSS_PROJECT_SYNTHESIS,
        MemoryEventType.VENTURE_BELIEF_UPDATE,
    }
    for event, targets in EVENT_WRITE_MAP.items():
        if WriteTarget.HINDSIGHT in targets:
            assert event in strategic, f"{event} must not write Hindsight"


def test_audit_report_exists():
    report = ROOT / "data/feedback-evidence/advoi-memory-retain-audit-01/audit.md"
    assert report.is_file(), f"missing audit report at {report}"
    text = report.read_text(encoding="utf-8")
    assert "P0 Hindsight" in text or "P0" in text
    assert "MemoryRouter.retain" in text


def test_orchestrate_routes_via_memory_router():
    """Regression: orchestration memory must not free-form operational_bridge retain."""
    src = _read(ADVOI_PKG / "squads" / "orchestrate.py")
    assert "retain_operational_unified" not in src
    assert "MemoryEventType.WORKFLOW_EVOLUTION" in src
    assert "MemoryRouter" in src


@pytest.mark.parametrize(
    "event",
    list(MemoryEventType),
)
def test_targets_for_never_returns_empty_without_skip(event: MemoryEventType):
    targets = targets_for(event)
    assert targets  # always at least one target (or would need SKIP explicitly)
    assert WriteTarget.SKIP not in targets or targets == (WriteTarget.SKIP,)
