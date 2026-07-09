"""Aether portfolio and routing tests."""

import json
from pathlib import Path

import pytest

from advoi.aether.gate import parse_gate_markdown
from advoi.aether.lifecycle import lifecycle_status, resolve_active_venture
from advoi.aether.portfolio import (
    load_ventures,
    reload_portfolio,
    venture_for_frame,
    portfolio_summary,
)
from advoi.aether.router import enrich_frame_context, route_summary


@pytest.fixture(autouse=True)
def _restore_portfolio():
    yield
    reload_portfolio()


def test_load_ventures_from_builtin_when_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("AETHER_PORTFOLIO_PATH", str(tmp_path / "missing.json"))
    reload_portfolio(path=tmp_path / "missing.json")
    summary = portfolio_summary()
    assert summary["total"] >= 3


def test_load_ventures_from_json(tmp_path, monkeypatch):
    cfg = tmp_path / "portfolio.json"
    cfg.write_text(
        json.dumps(
            {
                "ventures": [
                    {
                        "id": "test-venture",
                        "name": "Test Venture",
                        "status": "active",
                        "primary_frames": ["fleet_status"],
                        "squads": ["test-squad"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    ventures = load_ventures(path=cfg)
    assert len(ventures) == 1
    assert ventures[0].id == "test-venture"
    reload_portfolio(path=cfg)
    v = venture_for_frame("fleet_status")
    assert v is not None
    assert v.id == "test-venture"


def test_enrich_frame_context_adds_venture():
    detail = enrich_frame_context("fleet_status", {"status": "ok"})
    assert detail.get("aether_routed") is True
    assert "venture_id" in detail
    assert "gate_verdict" in detail


def test_route_summary_has_frame_routes():
    routes = route_summary()
    assert "portfolio" in routes
    assert "frame_routes" in routes
    assert "fleet_status" in routes["frame_routes"]


def test_parse_gate_markdown():
    text = "**Verdict:** pass\n**Active slug:** gem-dev-shop\n"
    snap = parse_gate_markdown(text)
    assert snap.found is True
    assert snap.verdict == "pass"
    assert snap.active_slug == "gem-dev-shop"


def test_resolve_active_venture_from_gate_slug():
    venture = resolve_active_venture(gate_active_slug="gem-dev-shop")
    assert venture is not None
    assert venture.id == "gem-dev-shop"


def test_lifecycle_status_shape():
    status = lifecycle_status()
    assert "gate" in status
    assert "frame_coverage" in status
    assert status["portfolio_total"] >= 3


def test_aether_api_portfolio(client):
    reload_portfolio()
    resp = client.get("/api/aether/portfolio")
    assert resp.status_code == 200
    data = resp.json()
    assert "portfolio" in data
    assert data["portfolio"]["total"] >= 3


def test_aether_api_status(client):
    resp = client.get("/api/aether/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "gate" in data
    assert "frame_coverage" in data
    assert "memory" in data
    assert "letta_health" in data["memory"]