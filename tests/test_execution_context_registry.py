"""Execution Context Registry (ECR) — load, resolve, and lifecycle wiring."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from advoi.aether.gate import GateSnapshot
from advoi.aether.lifecycle import lifecycle_status
from advoi.fleet.trigger import resolve_active_project
from advoi.ingestion.route import route_document
from advoi.portfolio.ecr import (
    load_execution_context,
    reload_execution_context,
    resolve_execution_target,
)
from advoi.routing import frame_runner


@pytest.fixture(autouse=True)
def _restore_ecr():
    yield
    reload_execution_context()


SAMPLE_ECR = """\
version: 1
active_execution_target:
  venture_id: firstmate-fleet
  fleet_slug: clapart
  github_repo: ActArtech/clapart
  develop_path: develop
  staging_url: https://clapart.example.com
ventures:
  - venture_id: advoi-system
    fleet_slug: advoi
    repo_path: /opt/advoi
    github_repo: ActArtech/advoi-system
    tags: [advoi-system, advoi]
  - venture_id: gem-dev-shop
    fleet_slug: gem-dev-shop
    repo_path: /opt/gem-dev-shop
    github_repo: ActArtech/gem-dev-shop
    tags: [gem-dev-shop, aether-active]
  - venture_id: clapart
    fleet_slug: clapart
    repo_path: /opt/clapart
    github_repo: ActArtech/clapart
    tags: [clapart]
"""


def test_load_execution_context_from_yaml(tmp_path, monkeypatch):
    cfg = tmp_path / "execution-context.yaml"
    cfg.write_text(SAMPLE_ECR, encoding="utf-8")
    monkeypatch.setenv("EXECUTION_CONTEXT_PATH", str(cfg))
    reload_execution_context(path=cfg)

    ctx = load_execution_context(path=cfg)
    assert ctx["version"] == 1
    assert ctx["active_execution_target"]["fleet_slug"] == "clapart"
    assert len(ctx["ventures"]) == 3


def test_resolve_execution_target_from_ecr(tmp_path, monkeypatch):
    cfg = tmp_path / "execution-context.yaml"
    cfg.write_text(SAMPLE_ECR, encoding="utf-8")
    monkeypatch.setenv("EXECUTION_CONTEXT_PATH", str(cfg))
    reload_execution_context(path=cfg)

    target = resolve_execution_target()
    assert target["venture_id"] == "firstmate-fleet"
    assert target["fleet_slug"] == "clapart"
    assert target["github_repo"] == "ActArtech/clapart"
    assert target["source"] == "ecr"


def test_resolve_execution_target_with_gate_slug(tmp_path, monkeypatch):
    cfg = tmp_path / "execution-context.yaml"
    cfg.write_text(SAMPLE_ECR, encoding="utf-8")
    monkeypatch.setenv("EXECUTION_CONTEXT_PATH", str(cfg))
    reload_execution_context(path=cfg)

    target = resolve_execution_target(gate_active_slug="gem-dev-shop")
    assert target["venture_id"] == "gem-dev-shop"
    assert target["fleet_slug"] == "gem-dev-shop"
    assert target["source"] == "gate"


def test_resolve_execution_target_fallback_chain(tmp_path, monkeypatch):
    missing = tmp_path / "missing.yaml"
    monkeypatch.setenv("EXECUTION_CONTEXT_PATH", str(missing))
    monkeypatch.delenv("FM_HERMES_PROJECT", raising=False)
    reload_execution_context(path=missing)

    target = resolve_execution_target()
    assert target["fleet_slug"] == "clapart"
    assert target["source"] == "fallback"

    monkeypatch.setenv("FM_HERMES_PROJECT", "advoi")
    reload_execution_context(path=missing)
    target = resolve_execution_target()
    assert target["fleet_slug"] == "advoi"
    assert target["venture_id"] == "advoi-system"
    assert target["source"] == "fallback"


def test_resolve_active_project_prefers_ecr(tmp_path, monkeypatch):
    cfg = tmp_path / "execution-context.yaml"
    cfg.write_text(SAMPLE_ECR, encoding="utf-8")
    monkeypatch.setenv("EXECUTION_CONTEXT_PATH", str(cfg))
    reload_execution_context(path=cfg)

    assert resolve_active_project() == "clapart"
    assert resolve_active_project(explicit="advoi") == "advoi"


def test_fleet_profile_snapshot_merges_ecr_when_missing(tmp_path, monkeypatch):
    cfg = tmp_path / "execution-context.yaml"
    cfg.write_text(SAMPLE_ECR, encoding="utf-8")
    monkeypatch.setenv("EXECUTION_CONTEXT_PATH", str(cfg))
    reload_execution_context(path=cfg)

    data_dir = tmp_path / "fleet-data"
    data_dir.mkdir()
    profile = frame_runner._fleet_profile_snapshot(data_dir)
    assert profile["profile_found"] is False
    assert profile["ecr_merged"] is True
    assert profile["active_slug"] == "clapart"


def test_ingestion_route_uses_ecr_default(tmp_path, monkeypatch):
    cfg = tmp_path / "execution-context.yaml"
    cfg.write_text(SAMPLE_ECR, encoding="utf-8")
    monkeypatch.setenv("EXECUTION_CONTEXT_PATH", str(cfg))
    reload_execution_context(path=cfg)

    route = route_document("generic planning notes", "notes.md")
    assert route["project_slug"] == "clapart"


def test_lifecycle_status_includes_execution_context(tmp_path, monkeypatch):
    cfg = tmp_path / "execution-context.yaml"
    cfg.write_text(SAMPLE_ECR, encoding="utf-8")
    monkeypatch.setenv("EXECUTION_CONTEXT_PATH", str(cfg))
    reload_execution_context(path=cfg)

    gate = GateSnapshot(found=True, verdict="pass", active_slug="gem-dev-shop")
    with patch("advoi.aether.lifecycle.load_gate_snapshot", return_value=gate):
        status = lifecycle_status()

    assert "execution_context" in status
    assert status["execution_context"]["venture_id"] == "gem-dev-shop"
    assert status["execution_context"]["source"] == "gate"
    assert status["execution_context"]["fleet_slug"] == "gem-dev-shop"


def test_aether_status_api_includes_execution_context(client, tmp_path, monkeypatch):
    cfg = tmp_path / "execution-context.yaml"
    cfg.write_text(SAMPLE_ECR, encoding="utf-8")
    monkeypatch.setenv("EXECUTION_CONTEXT_PATH", str(cfg))
    reload_execution_context(path=cfg)

    gate = GateSnapshot(found=False)
    with patch("advoi.aether.lifecycle.load_gate_snapshot", return_value=gate):
        resp = client.get("/api/aether/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "execution_context" in data
    assert data["execution_context"]["fleet_slug"] == "clapart"
    assert data["execution_context"]["source"] == "ecr"