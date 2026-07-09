"""Operational memory bridge tests."""

import os

import pytest

from advoi.memory.operational_bridge import (
    operational_diagnostics,
    recall_operational_unified,
    retain_operational_unified,
)


@pytest.mark.asyncio
async def test_retain_and_recall_local_store(tmp_path, monkeypatch):
    store = tmp_path / "ops.jsonl"
    monkeypatch.setenv("ADVOI_OPERATIONAL_STORE", str(store))
    monkeypatch.setenv("ADVOI_OPERATIONAL_STORE_ENABLED", "true")
    monkeypatch.setenv("LETTA_ENABLED", "false")

    results = await retain_operational_unified(
        "squad_lesson",
        {"summary": "Fleet scout ran OK for gem-dev-shop", "frame_id": "fleet_status"},
    )
    assert results.get("operational_store") is True

    rows, source = await recall_operational_unified("fleet scout")
    assert source == "operational_store"
    assert len(rows) >= 1
    assert "fleet scout" in rows[0]["text"].lower() or "Fleet" in rows[0]["text"]


@pytest.mark.asyncio
async def test_operational_diagnostics_disabled(monkeypatch):
    monkeypatch.setenv("LETTA_ENABLED", "false")
    diag = await operational_diagnostics()
    assert diag["letta_enabled"] is False
    assert diag["letta_health"]["ok"] is False