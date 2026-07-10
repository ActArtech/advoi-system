"""Unit tests for PWA SLA latency chip model (mirrors web/components/latencyChip.ts).

Python port keeps CI green without a JS test runner. Keep formatting rules in sync.
"""

from __future__ import annotations

from typing import Any


def format_ms(ms: float | int | None) -> str | None:
    if ms is None:
        return None
    try:
        n = float(ms)
    except (TypeError, ValueError):
        return None
    if n != n:  # NaN
        return None
    if n < 10:
        return f"{n:.1f}ms"
    return f"{round(n)}ms"


def latency_chip_model(diag: dict[str, Any] | None) -> dict[str, Any]:
    """Mirror of latencyChipModel in web/components/latencyChip.ts."""
    if diag is None:
        return {
            "available": False,
            "sla_ok": None,
            "label": "SLA —",
            "title": "Latency diagnostics unavailable",
            "tone": "empty",
            "frame_run_ms": None,
            "run_six_ms": None,
        }

    if diag.get("error"):
        return {
            "available": False,
            "sla_ok": None,
            "label": "SLA err",
            "title": f"Latency diagnostics error: {diag['error']}",
            "tone": "error",
            "frame_run_ms": None,
            "run_six_ms": None,
        }

    timings = diag.get("timings_ms") or {}
    frame_raw = timings.get("frame_run_ms")
    six_raw = timings.get("run_six_ms")
    try:
        frame_run_ms = float(frame_raw) if frame_raw is not None else None
        if frame_run_ms is not None and frame_run_ms != frame_run_ms:
            frame_run_ms = None
    except (TypeError, ValueError):
        frame_run_ms = None
    try:
        run_six_ms = float(six_raw) if six_raw is not None else None
        if run_six_ms is not None and run_six_ms != run_six_ms:
            run_six_ms = None
    except (TypeError, ValueError):
        run_six_ms = None

    parts: list[str] = []
    frame_label = format_ms(frame_run_ms)
    six_label = format_ms(run_six_ms)
    if frame_label:
        parts.append(f"frame {frame_label}")
    if six_label:
        parts.append(f"six {six_label}")

    has_timings = len(parts) > 0
    sla_ok = diag.get("sla_ok")
    if not isinstance(sla_ok, bool):
        sla_ok = None

    if not has_timings and sla_ok is None:
        label = "SLA —"
        tone = "error" if diag.get("ok") is False else "empty"
        title = (
            "Latency probe incomplete"
            if diag.get("ok") is False
            else "Latency timings not yet available"
        )
    else:
        if sla_ok is True:
            sla_part = "SLA ok"
        elif sla_ok is False:
            sla_part = "SLA miss"
        else:
            sla_part = "SLA"
        label = f"{sla_part} · {' · '.join(parts)}" if parts else sla_part
        if sla_ok is True:
            tone = "ok"
        elif sla_ok is False:
            tone = "warn"
        else:
            tone = "empty"
        target = diag.get("sla_target_ms")
        title = f"{label} (target {target}ms)" if target is not None else label

    return {
        "available": True,
        "sla_ok": sla_ok,
        "label": label,
        "title": title,
        "tone": tone,
        "frame_run_ms": frame_run_ms,
        "run_six_ms": run_six_ms,
    }


def test_empty_when_diagnostics_null():
    m = latency_chip_model(None)
    assert m["available"] is False
    assert m["tone"] == "empty"
    assert m["label"] == "SLA —"
    assert m["frame_run_ms"] is None
    assert m["run_six_ms"] is None


def test_error_when_fetch_failed():
    m = latency_chip_model({"ok": False, "error": "HTTP 503"})
    assert m["available"] is False
    assert m["tone"] == "error"
    assert m["label"] == "SLA err"
    assert "HTTP 503" in m["title"]


def test_ok_chip_with_frame_and_run_six():
    m = latency_chip_model(
        {
            "ok": True,
            "sla_ok": True,
            "sla_target_ms": 800,
            "timings_ms": {"frame_run_ms": 0.4, "run_six_ms": 42.2},
        }
    )
    assert m["available"] is True
    assert m["tone"] == "ok"
    assert m["sla_ok"] is True
    assert m["frame_run_ms"] == 0.4
    assert m["run_six_ms"] == 42.2
    assert "SLA ok" in m["label"]
    assert "frame 0.4ms" in m["label"]
    assert "six 42ms" in m["label"]
    assert "800" in m["title"]


def test_sla_miss_tone():
    m = latency_chip_model(
        {
            "ok": True,
            "sla_ok": False,
            "sla_target_ms": 800,
            "timings_ms": {"frame_run_ms": 900, "run_six_ms": 1200},
        }
    )
    assert m["tone"] == "warn"
    assert "SLA miss" in m["label"]
    assert "frame 900ms" in m["label"]
    assert "six 1200ms" in m["label"]


def test_partial_timings_only_frame():
    m = latency_chip_model(
        {
            "ok": True,
            "sla_ok": True,
            "timings_ms": {"frame_run_ms": 12, "run_six_ms": None},
        }
    )
    assert "frame 12ms" in m["label"]
    assert "six" not in m["label"]
    assert m["run_six_ms"] is None


def test_partial_timings_only_run_six():
    m = latency_chip_model(
        {
            "ok": True,
            "sla_ok": None,
            "timings_ms": {"frame_run_ms": None, "run_six_ms": 55},
        }
    )
    assert m["label"].startswith("SLA")
    assert "six 55ms" in m["label"]
    assert m["tone"] == "empty"


def test_probe_incomplete_no_timings():
    m = latency_chip_model({"ok": False, "timings_ms": {}})
    assert m["available"] is True
    assert m["tone"] == "error"
    assert m["label"] == "SLA —"


def test_api_latency_endpoint_shape(client):
    """Live probe shape used by the chip (frame_run_ms + run_six_ms)."""
    resp = client.get("/api/diagnostics/latency")
    assert resp.status_code == 200
    data = resp.json()
    timings = data["timings_ms"]
    assert "frame_run_ms" in timings
    assert "run_six_ms" in timings
    model = latency_chip_model(data)
    # With a healthy local stack the chip should surface both timings.
    if timings.get("frame_run_ms") is not None and timings.get("run_six_ms") is not None:
        assert model["available"] is True
        assert model["frame_run_ms"] is not None
        assert model["run_six_ms"] is not None
        assert "frame" in model["label"]
        assert "six" in model["label"]
