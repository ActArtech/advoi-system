"""Operational memory store tests."""

from __future__ import annotations

import pytest

from advoi.memory.operational_store import append_operational, recall_operational_local


@pytest.mark.asyncio
async def test_operational_store_append_and_recall(tmp_path, monkeypatch):
    path = tmp_path / "ops.jsonl"
    monkeypatch.setenv("ADVOI_OPERATIONAL_STORE", str(path))
    monkeypatch.setenv("ADVOI_OPERATIONAL_STORE_ENABLED", "true")

    ok = await append_operational(
        "squad_lesson",
        {"summary": "fleet-scout tick ok", "agent_id": "fleet-scout", "status": "ok"},
    )
    assert ok is True
    rows = await recall_operational_local("fleet-scout")
    assert rows
    assert "fleet-scout" in rows[0]["text"] or rows[0]["meta"]["agent_id"] == "fleet-scout"