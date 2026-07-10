"""T0: Guardian JSONL includes trace_id when OTEL is active (moat R6)."""

from __future__ import annotations

import json
import sys
import types

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
    assert "span_id" not in record


@pytest.mark.asyncio
async def test_guardian_jsonl_trace_id_null_when_otel_on_no_span(tmp_path, monkeypatch):
    log_path = tmp_path / "guardian.jsonl"
    monkeypatch.setenv("GUARDIAN_LOG_PATH", str(log_path))
    monkeypatch.setenv("OTEL_ENABLED", "true")
    monkeypatch.setattr(
        "advoi.memory.guardian_log.current_trace_id",
        lambda: None,
    )
    monkeypatch.setattr(
        "advoi.memory.guardian_log.current_span_id",
        lambda: None,
    )

    ok = await append_guardian_event("agent_tick_failed", {"agent": "guardian-sentinel"})
    assert ok is True

    record = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert "trace_id" in record
    assert record["trace_id"] is None
    assert "span_id" in record
    assert record["span_id"] is None


@pytest.mark.asyncio
async def test_guardian_jsonl_injects_trace_id_when_otel_active(tmp_path, monkeypatch):
    log_path = tmp_path / "guardian.jsonl"
    monkeypatch.setenv("GUARDIAN_LOG_PATH", str(log_path))
    monkeypatch.setenv("OTEL_ENABLED", "true")
    fake_tid = "0" * 31 + "a"
    fake_sid = "0" * 15 + "b"
    monkeypatch.setattr(
        "advoi.memory.guardian_log.current_trace_id",
        lambda: fake_tid,
    )
    monkeypatch.setattr(
        "advoi.memory.guardian_log.current_span_id",
        lambda: fake_sid,
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
    assert record["span_id"] == fake_sid


@pytest.mark.asyncio
async def test_guardian_jsonl_trace_from_mocked_span_context(tmp_path, monkeypatch):
    """End-to-end: mocked OTel span context → JSONL trace_id/span_id fields."""
    log_path = tmp_path / "guardian.jsonl"
    monkeypatch.setenv("GUARDIAN_LOG_PATH", str(log_path))
    monkeypatch.setenv("OTEL_ENABLED", "true")

    expected_trace = "a" * 32
    expected_span = "b" * 16

    class FakeSpanContext:
        is_valid = True
        trace_id = int(expected_trace, 16)
        span_id = int(expected_span, 16)

    class FakeSpan:
        def get_span_context(self) -> FakeSpanContext:
            return FakeSpanContext()

    otel_mod = types.ModuleType("opentelemetry")
    trace_mod = types.ModuleType("opentelemetry.trace")
    trace_mod.get_current_span = lambda: FakeSpan()  # type: ignore[attr-defined]
    otel_mod.trace = trace_mod  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "opentelemetry", otel_mod)
    monkeypatch.setitem(sys.modules, "opentelemetry.trace", trace_mod)

    ok = await append_guardian_event(
        "agent_restart_attempt",
        {"agent": "fleet-scout", "attempt": 1},
    )
    assert ok is True

    record = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert record["event_type"] == "agent_restart_attempt"
    assert record["trace_id"] == expected_trace
    assert record["span_id"] == expected_span
