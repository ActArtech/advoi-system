"""T0: Guardian JSONL includes trace_id when OTEL is active (moat R6)."""

from __future__ import annotations

import json

import pytest

from advoi.memory.guardian_log import append_guardian_event


@pytest.mark.asyncio
async def test_guardian_jsonl_no_trace_id_when_otel_off(tmp_path, monkeypatch):
    log_path = tmp_path / "guardian.jsonl"
    monkeypatch.setenv("GUARDIAN_LOG_PATH", str(log_path))
    monkeypatch.setenv("OTEL_ENABLED", "false")

    ok = await append_guardian_event("issue_detected", {"agent": "fleet-scout", "error": "x"})
    assert ok is True

    record = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert record["event_type"] == "issue_detected"
    assert "trace_id" not in record


@pytest.mark.asyncio
async def test_guardian_jsonl_trace_id_null_when_otel_on_no_span(tmp_path, monkeypatch):
    log_path = tmp_path / "guardian.jsonl"
    monkeypatch.setenv("GUARDIAN_LOG_PATH", str(log_path))
    monkeypatch.setenv("OTEL_ENABLED", "true")
    monkeypatch.setattr(
        "advoi.memory.guardian_log.current_trace_id",
        lambda: None,
    )

    ok = await append_guardian_event("agent_tick_failed", {"agent": "guardian-sentinel"})
    assert ok is True

    record = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert "trace_id" in record
    assert record["trace_id"] is None


@pytest.mark.asyncio
async def test_guardian_jsonl_injects_trace_id_when_otel_active(tmp_path, monkeypatch):
    log_path = tmp_path / "guardian.jsonl"
    monkeypatch.setenv("GUARDIAN_LOG_PATH", str(log_path))
    monkeypatch.setenv("OTEL_ENABLED", "true")
    fake_tid = "0" * 31 + "a"
    monkeypatch.setattr(
        "advoi.memory.guardian_log.current_trace_id",
        lambda: fake_tid,
    )

    ok = await append_guardian_event(
        "issue_detected",
        {"agent": "fleet-scout", "error": "tick failed"},
    )
    assert ok is True

    lines = [ln for ln in log_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["event_type"] == "issue_detected"
    assert record["payload"]["agent"] == "fleet-scout"
    assert record["trace_id"] == fake_tid
