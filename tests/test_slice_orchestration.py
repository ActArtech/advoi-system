"""Server-side slice orchestration (presets, chains, wave modes)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from advoi.routing.slice_orchestration import (
    DEFAULT_SIX_FRAME_IDS,
    chunk_frame_waves,
    describe_wave_plan,
    order_pulse_last,
    resolve_slice_run,
    run_frames_with_mode,
    run_slice_orchestrate,
    slice_catalog,
)


def test_slice_catalog_matches_presets():
    catalog = slice_catalog()
    assert len(catalog["presets"]) == 4
    assert len(catalog["chains"]) == 5
    assert catalog["defaultSix"] == list(DEFAULT_SIX_FRAME_IDS)


def test_resolve_slice_run_preset_ops_core():
    ids, mode, chain, dispatch = resolve_slice_run(preset_id="ops_core")
    assert ids == ["fleet_status", "open_briefs", "guardian_status"]
    assert mode == "wave"
    assert chain is None
    assert dispatch is False


def test_resolve_slice_run_chain_ops_intel():
    ids, mode, chain, dispatch = resolve_slice_run(chain_id="ops_then_intel")
    assert ids == []
    assert chain is not None
    assert chain["chainId"] == "ops_then_intel"
    assert len(chain["stages"]) == 2
    assert dispatch is False


def test_resolve_slice_run_chain_dispatch_after():
    _, _, chain, dispatch = resolve_slice_run(chain_id="intel_then_dispatch")
    assert chain is not None
    assert dispatch is True


def test_resolve_slice_run_unknown_preset_raises():
    with pytest.raises(ValueError, match="Unknown preset_id"):
        resolve_slice_run(preset_id="missing")


def test_order_pulse_last():
    assert order_pulse_last(
        ["systems_pulse", "fleet_status", "open_briefs"]
    ) == ["fleet_status", "open_briefs", "systems_pulse"]


def test_describe_wave_plan_ops_core():
    ids, mode, _, _ = resolve_slice_run(preset_id="ops_core")
    plan = describe_wave_plan(ids, mode)
    assert plan["waveCount"] == 2
    assert plan["waves"][0]["frameIds"] == ["fleet_status", "open_briefs"]


@pytest.mark.asyncio
async def test_run_frames_with_mode_stagger_calls_sequential():
    mock_results = []
    for fid in ("fleet_status", "open_briefs"):
        row = AsyncMock()
        row.frame_id = fid
        row.status = "ok"
        mock_results.append(row)

    with patch(
        "advoi.routing.frame_runner.run_frame",
        new_callable=AsyncMock,
        side_effect=mock_results,
    ) as run_frame:
        results = await run_frames_with_mode(
            ["fleet_status", "open_briefs"],
            "stagger",
            confirmed=True,
        )
        assert len(results) == 2
        assert run_frame.await_count == 2


@pytest.mark.asyncio
async def test_run_slice_orchestrate_preset_wave():
    mock_result = AsyncMock()
    mock_result.frame_id = "fleet_status"
    mock_result.agent_id = "fleet-scout"
    mock_result.status = "ok"
    mock_result.spoken_summary = "Fleet ok"
    mock_result.detail = {"agents_used": ["fleet-scout"]}

    with (
        patch(
            "advoi.routing.slice_orchestration.run_frames_with_mode",
            new_callable=AsyncMock,
            return_value=[mock_result],
        ),
        patch(
            "advoi.squads.orchestrate.retain_orchestration_memory",
            new_callable=AsyncMock,
        ),
    ):
        payload = await run_slice_orchestrate(
            preset_id="morning_pulse",
            confirmed=True,
            retain_memory=False,
        )
    assert payload["mode"] == "stagger"
    assert payload["preset_id"] == "morning_pulse"
    assert payload["fail_count"] == 0
    assert payload["wave_plan"]["waveCount"] == 1


@pytest.mark.asyncio
async def test_run_slice_orchestrate_chain_two_stages():
    stage_a = AsyncMock()
    stage_a.frame_id = "fleet_status"
    stage_a.agent_id = "fleet-scout"
    stage_a.status = "ok"
    stage_a.spoken_summary = "a"
    stage_a.detail = {}

    stage_b = AsyncMock()
    stage_b.frame_id = "open_briefs"
    stage_b.agent_id = "brief-curator"
    stage_b.status = "ok"
    stage_b.spoken_summary = "b"
    stage_b.detail = {}

    with (
        patch(
            "advoi.routing.slice_orchestration.run_frames_with_mode",
            new_callable=AsyncMock,
            side_effect=[[stage_a], [stage_b]],
        ) as run_mode,
        patch(
            "advoi.squads.orchestrate.retain_orchestration_memory",
            new_callable=AsyncMock,
        ),
    ):
        payload = await run_slice_orchestrate(
            chain_id="morning_then_ops",
            confirmed=True,
            retain_memory=False,
        )

    assert payload["mode"] == "chain"
    assert payload["chain_id"] == "morning_then_ops"
    assert run_mode.await_count == 2
    assert len(payload["results"]) == 2
    assert payload["wave_plan"]["stages"][0]["presetId"] == "morning_pulse"


def test_api_slice_catalog(client: TestClient):
    resp = client.get("/api/agents/slice-catalog")
    assert resp.status_code == 200
    data = resp.json()
    assert any(p["id"] == "ops_core" for p in data["presets"])


def test_api_orchestrate_preset_ops_core(client: TestClient):
    resp = client.post(
        "/api/agents/orchestrate",
        json={"preset_id": "ops_core", "confirmed": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "wave"
    assert data["preset_id"] == "ops_core"
    assert len(data["results"]) == 3
    assert data["wave_plan"]["waveCount"] == 2


def test_api_orchestrate_wave_mode(client: TestClient):
    resp = client.post(
        "/api/agents/orchestrate",
        json={
            "frame_ids": ["fleet_status", "open_briefs", "guardian_status"],
            "mode": "wave",
            "confirmed": True,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "wave"
    assert data["wave_plan"]["waveCount"] == 2


def test_api_orchestrate_unknown_preset_422(client: TestClient):
    resp = client.post(
        "/api/agents/orchestrate",
        json={"preset_id": "not_real"},
    )
    assert resp.status_code == 422


def test_chunk_frame_waves_wave_pairs():
    ids = ["a", "b", "c", "d", "e"]
    assert chunk_frame_waves(ids, "wave") == [["a", "b"], ["c", "d"], ["e"]]