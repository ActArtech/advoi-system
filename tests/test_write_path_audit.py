"""Guardian write-path audit — static + behavioral guards (advoi-arch-write-path-audit-01).

Forbids:
- fm-bridge / hermes-trigger shell outside ``advoi/fleet/``
- Production call sites of ``invoke_fleet_trigger`` without Guardian tokens
- Voice importing low-level bridge shell helpers
- Ungated free-form work dispatch from the HTTP fleet trigger path
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ADVOI_PKG = ROOT / "advoi"

# Only the fleet package may resolve/exec the FirstMate bridge.
_BRIDGE_SHELL_ALLOWED_PREFIXES = (
    "advoi/fleet/",
)

# Production modules that may call invoke_fleet_trigger (must prove Guardian).
_INVOKE_ALLOWED_PREFIXES = (
    "advoi/fleet/",
    "advoi/ingestion/",
)

# Patterns that indicate a direct bridge shell path.
_BRIDGE_SHELL_PATTERNS = (
    re.compile(r"resolve_fleet_exec\s*\("),
    re.compile(r"fm-bridge\.sh"),
    re.compile(r"fm-hermes-trigger\.sh"),
    re.compile(r"create_subprocess_exec"),
)

_GUARDIAN_TOKEN_MARKERS = (
    "guardian_allowed",
    "guardian_status",
)


def _rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _iter_py(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_audit_report_exists():
    report = ROOT / "data/feedback-evidence/advoi-arch-write-path-audit-01/audit.md"
    assert report.is_file(), f"missing audit report at {report}"
    text = report.read_text(encoding="utf-8")
    assert "P0" in text
    assert "invoke_fleet_trigger" in text
    assert "Guardian" in text or "guardian" in text


def test_only_fleet_package_resolves_or_execs_bridge():
    """No production package outside fleet may shell to fm-bridge / hermes-trigger.

    Note: routing may ``create_subprocess_exec`` for *readonly* fleet scout
    scripts or agent docker control — that is not the write-path bridge.
    """
    offenders: list[str] = []
    for path in _iter_py(ADVOI_PKG):
        rel = _rel(path)
        if any(rel.startswith(p) for p in _BRIDGE_SHELL_ALLOWED_PREFIXES):
            continue
        src = _read(path)
        # resolve_fleet_exec is the Python entry to bridge argv — fleet only.
        if re.search(r"\bresolve_fleet_exec\s*\(", src):
            offenders.append(f"{rel}: resolve_fleet_exec")
        # Literal bridge script names outside fleet package.
        if re.search(r"fm-bridge\.sh|fm-hermes-trigger\.sh", src):
            offenders.append(f"{rel}: bridge script path literal")
        # Direct env override of bridge script outside fleet.
        if "ADVOI_FM_BRIDGE_SCRIPT" in src or "FIRSTMATE_TRIGGER_SCRIPT" in src:
            offenders.append(f"{rel}: bridge env wiring")
    assert offenders == [], f"bridge shell outside fleet: {offenders}"


def test_invoke_fleet_trigger_call_sites_are_gated_packages():
    """Only fleet + ingestion (post-approve) may call low-level invoke in production."""
    call_re = re.compile(r"\binvoke_fleet_trigger\s*\(")
    offenders: list[str] = []
    for path in _iter_py(ADVOI_PKG):
        rel = _rel(path)
        if any(rel.startswith(p) for p in _INVOKE_ALLOWED_PREFIXES):
            continue
        src = _read(path)
        if call_re.search(src):
            offenders.append(rel)
    assert offenders == [], f"invoke_fleet_trigger outside allowed packages: {offenders}"


def test_ingestion_invoke_passes_guardian_token():
    """Ingestion free-form work must pass guardian_allowed after evaluate_fleet_confirmation."""
    src = _read(ADVOI_PKG / "ingestion" / "pipeline.py")
    assert "evaluate_fleet_confirmation" in src
    assert "invoke_fleet_trigger" in src
    # Every invoke_fleet_trigger in ingestion must include guardian_allowed=True.
    for match in re.finditer(r"invoke_fleet_trigger\s*\((.*?)\)", src, re.S):
        args = match.group(1)
        assert "guardian_allowed" in args, (
            f"ingestion invoke missing guardian_allowed: {args[:120]!r}"
        )


def test_api_fleet_trigger_does_not_bare_invoke():
    """HTTP fleet trigger must not call unguarded invoke_fleet_trigger."""
    src = _read(ADVOI_PKG / "api" / "app.py")
    # Endpoint still may import fleet_trigger_from_voice only for writes.
    assert "fleet_trigger_from_voice" in src
    # No direct invoke call (P0 V2 removed). Name may appear only in comments.
    assert not re.search(r"\binvoke_fleet_trigger\s*\(", src)
    assert "from advoi.fleet.trigger import" in src
    # Import must not pull the low-level invoke for this endpoint.
    import_block = re.search(
        r"from advoi\.fleet\.trigger import \((.*?)\)",
        src,
        re.S,
    )
    if import_block:
        assert "invoke_fleet_trigger" not in import_block.group(1)


def test_voice_does_not_import_low_level_bridge_shell():
    """Voice may use fleet_trigger_from_voice but not resolve_fleet_exec / bare bridge."""
    for path in _iter_py(ADVOI_PKG / "voice"):
        src = _read(path)
        rel = _rel(path)
        assert "resolve_fleet_exec" not in src, rel
        assert "from advoi.fleet.bridge" not in src, rel
        # Bare low-level invoke is forbidden in voice (must use from_voice wrapper).
        if "invoke_fleet_trigger" in src:
            # Allow only in comments/docstrings mentioning the name.
            if re.search(r"\binvoke_fleet_trigger\s*\(", src):
                pytest.fail(f"voice must not call invoke_fleet_trigger: {rel}")


def test_aether_does_not_invoke_fm_bridge():
    """Aether may read/export gate artifacts but must not shell fm-bridge."""
    for path in _iter_py(ADVOI_PKG / "aether"):
        src = _read(path)
        rel = _rel(path)
        assert "invoke_fleet_trigger" not in src, rel
        assert "fleet_trigger_from_voice" not in src, rel
        assert "resolve_fleet_exec" not in src, rel


def test_invoke_hard_gate_function_present():
    src = _read(ADVOI_PKG / "fleet" / "trigger.py")
    assert "_guardian_permits_fleet_invoke" in src
    assert "guardian_required" in src
    assert "guardian_allowed" in src


@pytest.mark.asyncio
async def test_invoke_rejects_without_guardian_token(monkeypatch: pytest.MonkeyPatch):
    """Behavioral T0: default confirmation policy blocks unguarded fm-bridge invoke."""
    monkeypatch.setenv("ADVOI_FLEET_MOCK", "true")
    monkeypatch.setenv("ADVOI_CONFIRMATION_REQUIRED", "true")
    from advoi.fleet.trigger import invoke_fleet_trigger

    denied = await invoke_fleet_trigger("arm", project="clapart")
    assert denied["ok"] is False
    assert denied["status"] == "guardian_required"
    assert denied.get("guardian") is True


@pytest.mark.asyncio
async def test_invoke_allows_with_guardian_token(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ADVOI_FLEET_MOCK", "true")
    monkeypatch.setenv("ADVOI_CONFIRMATION_REQUIRED", "true")
    from advoi.fleet.trigger import invoke_fleet_trigger

    ok = await invoke_fleet_trigger(
        "arm",
        project="clapart",
        guardian_allowed=True,
    )
    assert ok["ok"] is True
    assert ok["status"] == "mock"


@pytest.mark.asyncio
async def test_invoke_allows_when_confirmation_disabled(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ADVOI_FLEET_MOCK", "true")
    monkeypatch.setenv("ADVOI_CONFIRMATION_REQUIRED", "false")
    from advoi.fleet.trigger import invoke_fleet_trigger

    ok = await invoke_fleet_trigger("arm", project="clapart")
    assert ok["ok"] is True
    assert ok["status"] == "mock"


def test_fleet_trigger_from_voice_is_sole_public_gated_entry():
    """Structured high-risk actions stay on fleet_trigger_from_voice."""
    src = _read(ADVOI_PKG / "fleet" / "trigger.py")
    assert "evaluate_fleet_confirmation" in src
    assert "async def fleet_trigger_from_voice" in src
    # After gate, inner invokes mark allowed.
    assert 'guardian_status="allowed"' in src
