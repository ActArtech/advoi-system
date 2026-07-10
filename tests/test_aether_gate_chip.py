"""Unit tests for PWA Aether gate chip model (mirrors web/components/aetherGateChip.ts).

Python port keeps CI green without a JS test runner. Keep formatting rules in sync.
"""

from __future__ import annotations

from typing import Any


def _normalize_verdict(raw: Any) -> str | None:
    if raw is None:
        return None
    v = str(raw).strip().lower()
    if not v:
        return None
    if v in {"pass", "go"}:
        return "pass"
    if v == "hold":
        return "hold"
    if v in {"fail", "blocked", "no-go", "no go"}:
        return "fail"
    if v == "unknown":
        return "unknown"
    return v


def _tone_for_verdict(verdict: str | None, found: bool) -> str:
    if not found or verdict is None or verdict == "unknown":
        return "empty"
    if verdict == "pass":
        return "ok"
    if verdict == "hold":
        return "warn"
    if verdict == "fail":
        return "error"
    return "empty"


def aether_gate_chip_model(status: dict[str, Any] | None) -> dict[str, Any]:
    """Mirror of aetherGateChipModel in web/components/aetherGateChip.ts."""
    if status is None:
        return {
            "available": False,
            "verdict": None,
            "active_slug": None,
            "label": "Gate —",
            "title": "Aether status unavailable",
            "tone": "empty",
            "found": False,
        }

    if status.get("error"):
        return {
            "available": False,
            "verdict": None,
            "active_slug": None,
            "label": "Gate err",
            "title": f"Aether status error: {status['error']}",
            "tone": "error",
            "found": False,
        }

    gate = status.get("gate")
    if gate is None:
        return {
            "available": True,
            "verdict": None,
            "active_slug": None,
            "label": "Gate —",
            "title": "Aether gate not present in status",
            "tone": "empty",
            "found": False,
        }

    found = bool(gate.get("found"))
    verdict = _normalize_verdict(gate.get("verdict"))
    raw_slug = gate.get("active_slug")
    active_slug = str(raw_slug).strip() if raw_slug is not None and str(raw_slug).strip() else None

    if not found:
        path = gate.get("path")
        title = f"Aether gate not found ({path})" if path else "Aether gate not found"
        return {
            "available": True,
            "verdict": None,
            "active_slug": active_slug,
            "label": "Gate —",
            "title": title,
            "tone": "empty",
            "found": False,
        }

    verdict_part = f"Gate {verdict}" if verdict and verdict != "unknown" else "Gate"
    parts = [verdict_part]
    if active_slug:
        parts.append(active_slug)
    label = " · ".join(parts)

    tone = _tone_for_verdict(verdict, found)
    title_parts = [label]
    active_venture = status.get("active_venture") or {}
    if active_venture.get("name"):
        title_parts.append(f"venture {active_venture['name']}")
    if gate.get("path"):
        title_parts.append(str(gate["path"]))

    return {
        "available": True,
        "verdict": verdict,
        "active_slug": active_slug,
        "label": label,
        "title": " · ".join(title_parts),
        "tone": tone,
        "found": True,
    }


def test_empty_when_status_null():
    m = aether_gate_chip_model(None)
    assert m["available"] is False
    assert m["tone"] == "empty"
    assert m["label"] == "Gate —"
    assert m["verdict"] is None
    assert m["active_slug"] is None


def test_error_when_fetch_failed():
    m = aether_gate_chip_model({"ok": False, "error": "HTTP 502"})
    assert m["available"] is False
    assert m["tone"] == "error"
    assert m["label"] == "Gate err"
    assert "HTTP 502" in m["title"]


def test_gate_not_found():
    m = aether_gate_chip_model(
        {
            "gate": {
                "found": False,
                "verdict": "unknown",
                "active_slug": None,
                "path": "/opt/firstmate-fleet/aether-gate-latest.md",
            }
        }
    )
    assert m["available"] is True
    assert m["found"] is False
    assert m["tone"] == "empty"
    assert m["label"] == "Gate —"
    assert "not found" in m["title"]


def test_pass_with_active_slug():
    m = aether_gate_chip_model(
        {
            "gate": {
                "found": True,
                "verdict": "pass",
                "active_slug": "gem-dev-shop",
                "path": "/opt/firstmate-fleet/aether-gate-latest.md",
            },
            "active_venture": {"id": "gem-dev-shop", "name": "Gem Dev Shop"},
            "active_venture_resolved": True,
        }
    )
    assert m["available"] is True
    assert m["found"] is True
    assert m["tone"] == "ok"
    assert m["verdict"] == "pass"
    assert m["active_slug"] == "gem-dev-shop"
    assert m["label"] == "Gate pass · gem-dev-shop"
    assert "Gem Dev Shop" in m["title"]


def test_hold_tone():
    m = aether_gate_chip_model(
        {
            "gate": {
                "found": True,
                "verdict": "hold",
                "active_slug": "clapart",
            }
        }
    )
    assert m["tone"] == "warn"
    assert m["label"] == "Gate hold · clapart"
    assert m["verdict"] == "hold"


def test_fail_tone():
    m = aether_gate_chip_model(
        {
            "gate": {
                "found": True,
                "verdict": "fail",
                "active_slug": "advoi",
            }
        }
    )
    assert m["tone"] == "error"
    assert "Gate fail" in m["label"]
    assert "advoi" in m["label"]


def test_unknown_verdict_with_slug():
    m = aether_gate_chip_model(
        {
            "gate": {
                "found": True,
                "verdict": "unknown",
                "active_slug": "advoi",
            }
        }
    )
    assert m["tone"] == "empty"
    assert m["label"] == "Gate · advoi"
    assert m["active_slug"] == "advoi"


def test_verdict_without_slug():
    m = aether_gate_chip_model(
        {
            "gate": {
                "found": True,
                "verdict": "pass",
                "active_slug": None,
            }
        }
    )
    assert m["label"] == "Gate pass"
    assert m["active_slug"] is None
    assert m["tone"] == "ok"


def test_normalize_go_and_blocked():
    go = aether_gate_chip_model({"gate": {"found": True, "verdict": "go", "active_slug": "x"}})
    assert go["verdict"] == "pass"
    assert go["tone"] == "ok"
    blocked = aether_gate_chip_model(
        {"gate": {"found": True, "verdict": "blocked", "active_slug": "y"}}
    )
    assert blocked["verdict"] == "fail"
    assert blocked["tone"] == "error"


def test_missing_gate_key():
    m = aether_gate_chip_model({"portfolio_total": 3})
    assert m["label"] == "Gate —"
    assert m["available"] is True
    assert m["found"] is False


def test_api_aether_status_feeds_chip(client):
    """Live /api/aether/status shape used by the PWA gate chip."""
    resp = client.get("/api/aether/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "gate" in data
    gate = data["gate"]
    assert "verdict" in gate
    assert "active_slug" in gate
    assert "found" in gate
    model = aether_gate_chip_model(data)
    assert model["available"] is True
    assert model["label"].startswith("Gate")
    # Chip always exposes slug field (null when gate has none).
    assert "active_slug" in model
    if gate.get("found") and gate.get("active_slug"):
        assert model["active_slug"] == gate["active_slug"]
        assert gate["active_slug"] in model["label"]
    if gate.get("found") and gate.get("verdict") not in (None, "unknown"):
        assert model["verdict"] is not None
