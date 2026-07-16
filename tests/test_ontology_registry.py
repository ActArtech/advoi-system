"""Ontology registry — vocabulary membership for frames, agents, ventures."""

from pathlib import Path

import pytest

from advoi.aether.portfolio import reload_portfolio
from advoi.ontology import (
    is_valid_agent_id,
    is_valid_frame_id,
    is_valid_venture_id,
    list_agents,
    list_frames,
    list_ventures,
)
from advoi.ontology import registry as ontology_registry

EXPECTED_FRAMES = (
    "fleet_status",
    "open_briefs",
    "queue_deep_review",
    "systems_pulse",
    "memory_health",
    "guardian_status",
)

EXPECTED_AGENTS = (
    "fleet-scout",
    "brief-curator",
    "review-queue",
    "systems-pulse",
    "memory-scout",
    "guardian-sentinel",
)

# Portfolio.json ventures (present in repo); builtin fallback has first three.
PORTFOLIO_VENTURES = (
    "advoi-system",
    "firstmate-fleet",
    "hermes-beacon",
    "gem-dev-shop",
)

BUILTIN_VENTURES = (
    "advoi-system",
    "firstmate-fleet",
    "hermes-beacon",
    "gem-dev-shop",
)


@pytest.fixture(autouse=True)
def _restore_portfolio():
    yield
    reload_portfolio()


def test_list_frames_has_six():
    frames = list_frames()
    assert len(frames) == 6
    assert frames == list(EXPECTED_FRAMES)


def test_is_valid_frame_id():
    for fid in EXPECTED_FRAMES:
        assert is_valid_frame_id(fid) is True
    assert is_valid_frame_id("not_a_frame") is False
    assert is_valid_frame_id("") is False


def test_list_agents_has_six():
    agents = list_agents()
    assert len(agents) == 6
    assert set(agents) == set(EXPECTED_AGENTS)


def test_is_valid_agent_id():
    for aid in EXPECTED_AGENTS:
        assert is_valid_agent_id(aid) is True
    assert is_valid_agent_id("not-an-agent") is False
    assert is_valid_agent_id("") is False


def test_portfolio_ventures_from_json():
    """With data/aether/portfolio.json present, all four ventures are valid."""
    portfolio = Path("data/aether/portfolio.json")
    assert portfolio.is_file(), "repo portfolio.json required for this test"
    reload_portfolio(path=portfolio)

    ventures = list_ventures()
    for vid in PORTFOLIO_VENTURES:
        assert is_valid_venture_id(vid) is True, vid
        assert vid in ventures
    assert is_valid_venture_id("nonexistent-venture") is False


def test_portfolio_builtin_fallback(tmp_path):
    """Missing portfolio file falls back to builtin venture ids."""
    missing = tmp_path / "missing-portfolio.json"
    reload_portfolio(path=missing)

    for vid in BUILTIN_VENTURES:
        assert is_valid_venture_id(vid) is True, vid
    assert is_valid_venture_id("nonexistent-venture") is False


def test_package_exports_match_registry():
    assert ontology_registry.is_valid_frame_id is is_valid_frame_id
    assert ontology_registry.list_frames is list_frames
    assert ontology_registry.list_agents is list_agents
