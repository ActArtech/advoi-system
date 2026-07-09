"""Multi-agent orchestrate CLI tests."""

from __future__ import annotations

import json

import pytest

from advoi.routing.orchestrate_cli import _run


@pytest.mark.asyncio
async def test_orchestrate_json_includes_six_frames(capsys):
    code = await _run("json", refresh=True)
    assert code == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert len(payload["results"]) == 6
    assert len(payload["agents"]) == 6
    assert "spoken_summary" in payload


@pytest.mark.asyncio
async def test_orchestrate_six_mode():
    code = await _run("six", refresh=True)
    assert code == 0


@pytest.mark.asyncio
async def test_orchestrate_six_squads_mode():
    code = await _run("six-squads", refresh=True, dispatch_squads=True)
    assert code == 0


@pytest.mark.asyncio
async def test_orchestrate_prewarm_only():
    code = await _run("prewarm", refresh=False)
    assert code == 0