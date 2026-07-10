"""T0: fm-bridge invoke idempotency (60s dedupe window)."""

from __future__ import annotations

import pytest

from advoi.analytics.pel import memory_rows, reset_memory_store
from advoi.fleet.idempotency import (
    clear_idempotency_cache,
    get_idempotent_result,
    normalize_idempotency_key,
    store_idempotent_result,
)
from advoi.fleet.trigger import fleet_trigger_from_voice, invoke_fleet_trigger


@pytest.fixture(autouse=True)
def _clean_idem_and_pel(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ADVOI_FLEET_MOCK", "true")
    monkeypatch.setenv("ADVOI_PEL_MEMORY", "true")
    clear_idempotency_cache()
    reset_memory_store()
    yield
    clear_idempotency_cache()
    reset_memory_store()


def test_normalize_idempotency_key():
    assert normalize_idempotency_key(None) is None
    assert normalize_idempotency_key("") is None
    assert normalize_idempotency_key("  ") is None
    assert normalize_idempotency_key("  abc  ") == "abc"
    assert normalize_idempotency_key("x" * 257) is None
    assert normalize_idempotency_key("x" * 256) == "x" * 256


def test_store_skips_confirmation_required():
    store_idempotent_result("k1", {"status": "confirmation_required", "ok": False})
    assert get_idempotent_result("k1") is None
    store_idempotent_result("k1", {"status": "mock", "ok": True, "message": "arm"})
    hit = get_idempotent_result("k1")
    assert hit is not None
    assert hit["deduped"] is True
    assert hit["message"] == "arm"


@pytest.mark.asyncio
async def test_duplicate_invoke_within_window_deduped():
    """T0: same idempotency_key within 60s returns prior result; no re-execution."""
    key = "t0-arm-clapart-once"
    # Post-gate token (simulates fleet_trigger_from_voice after Guardian).
    g = {"guardian_allowed": True}
    first = await invoke_fleet_trigger(
        "arm", project="clapart", idempotency_key=key, **g
    )
    assert first["ok"] is True
    assert first["status"] == "mock"
    assert first.get("deduped") is not True
    assert first["idempotency_key"] == key

    second = await invoke_fleet_trigger(
        "arm", project="clapart", idempotency_key=key, **g
    )
    assert second["ok"] is True
    assert second["status"] == "mock"
    assert second["deduped"] is True
    assert second["message"] == first["message"]
    assert second["project"] == first["project"]
    assert second["output"] == first["output"]

    # Different key still executes.
    other = await invoke_fleet_trigger(
        "arm",
        project="clapart",
        idempotency_key="t0-arm-clapart-other",
        **g,
    )
    assert other["ok"] is True
    assert other.get("deduped") is not True

    # Without a key: always executes (two mock rows).
    a = await invoke_fleet_trigger("arm", project="clapart", **g)
    b = await invoke_fleet_trigger("arm", project="clapart", **g)
    assert a.get("deduped") is not True
    assert b.get("deduped") is not True

    # Only first keyed invoke + other key + two unkeyed = 4 fleet_trigger PEL rows.
    # Second keyed call must not re-emit.
    fleet_rows = [r for r in memory_rows() if r["type"] == "fleet_trigger"]
    assert len(fleet_rows) == 4


@pytest.mark.asyncio
async def test_duplicate_voice_action_deduped(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ADVOI_CONFIRMATION_REQUIRED", "false")
    key = "t0-wake-voice"
    first = await fleet_trigger_from_voice(
        "wake_firstmate",
        transcript="wake firstmate on clapart",
        confirmed=True,
        idempotency_key=key,
    )
    assert first["ok"] is True
    assert first["action"] == "wake_firstmate"
    second = await fleet_trigger_from_voice(
        "wake_firstmate",
        transcript="wake firstmate on clapart",
        confirmed=True,
        idempotency_key=key,
    )
    assert second["deduped"] is True
    assert second["action"] == "wake_firstmate"
    assert second["spoken"] == first["spoken"]


@pytest.mark.asyncio
async def test_api_header_idempotency_key(client, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ADVOI_FLEET_MOCK", "true")
    monkeypatch.setenv("ADVOI_CONFIRMATION_REQUIRED", "false")
    payload = {
        "action": "wake_firstmate",
        "confirmed": True,
        "project": "clapart",
    }
    headers = {"Idempotency-Key": "api-header-key-1"}
    r1 = client.post("/api/fleet/trigger", json=payload, headers=headers)
    r2 = client.post("/api/fleet/trigger", json=payload, headers=headers)
    assert r1.status_code == 200
    assert r2.status_code == 200
    d1, d2 = r1.json(), r2.json()
    assert d1["ok"] is True
    assert d2["deduped"] is True
    assert d2["output"] == d1["output"]


@pytest.mark.asyncio
async def test_api_body_idempotency_key(client, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ADVOI_FLEET_MOCK", "true")
    monkeypatch.setenv("ADVOI_CONFIRMATION_REQUIRED", "false")
    payload = {
        "action": "wake_firstmate",
        "confirmed": True,
        "project": "clapart",
        "idempotency_key": "api-body-key-1",
    }
    r1 = client.post("/api/fleet/trigger", json=payload)
    r2 = client.post("/api/fleet/trigger", json=payload)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r2.json()["deduped"] is True


@pytest.mark.asyncio
async def test_confirmation_required_not_cached(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ADVOI_CONFIRMATION_REQUIRED", "true")
    key = "t0-confirm-gate"
    denied = await fleet_trigger_from_voice(
        "wake_firstmate",
        transcript="wake firstmate",
        confirmed=False,
        idempotency_key=key,
    )
    assert denied["status"] == "confirmation_required"
    assert denied.get("deduped") is not True

    # Same key with confirm must still execute (not stuck on confirmation_required).
    allowed = await fleet_trigger_from_voice(
        "wake_firstmate",
        transcript="wake firstmate confirm",
        confirmed=True,
        idempotency_key=key,
    )
    assert allowed.get("ok") is True
    assert allowed.get("deduped") is not True
