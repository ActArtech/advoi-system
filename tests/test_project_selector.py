"""Project selector catalog and voice matching (mirrors web/lib/portfolio/projectModel.ts)."""

from __future__ import annotations

import re

import pytest

from advoi.aether.portfolio import reload_portfolio
from advoi.portfolio.ecr import clear_session_active_venture, resolve_execution_target, set_session_active_venture
from advoi.portfolio.projects import (
    activate_project,
    build_projects_catalog,
    classify_project_voice_intent,
    match_venture_id,
    spoken_project_switch,
)


@pytest.fixture(autouse=True)
def _reset_portfolio_session():
    clear_session_active_venture()
    reload_portfolio()
    yield
    clear_session_active_venture()
    reload_portfolio()


def test_build_projects_catalog_shape():
    catalog = build_projects_catalog()
    assert "ventures" in catalog
    assert len(catalog["ventures"]) >= 3
    first = catalog["ventures"][0]
    assert "functions" in first
    assert any(fn["kind"] == "frame" for fn in first["functions"])


def test_match_venture_id_aliases():
    assert match_venture_id("gem-dev-shop") == "gem-dev-shop"
    assert match_venture_id("gem dev shop") == "gem-dev-shop"
    assert match_venture_id("advoi") == "advoi-system"
    assert match_venture_id("hermes") == "hermes-beacon"


@pytest.mark.parametrize(
    "transcript,action,venture_id",
    [
        ("switch to gem dev shop", "switch_project", "gem-dev-shop"),
        ("open advoi system", "switch_project", "advoi-system"),
        ("activate firstmate fleet", "switch_project", "firstmate-fleet"),
        ("work on hermes beacon", "switch_project", "hermes-beacon"),
    ],
)
def test_classify_project_voice_switch(transcript, action, venture_id):
    intent = classify_project_voice_intent(transcript)
    assert intent is not None
    assert intent["action"] == action
    assert intent["venture_id"] == venture_id


def test_classify_project_voice_activate_function():
    intent = classify_project_voice_intent("fleet status on advoi")
    assert intent is not None
    assert intent["action"] == "activate_function"
    assert intent["venture_id"] == "advoi-system"
    assert intent["frame_id"] == "fleet_status"


def test_activate_project_sets_session_override():
    result = activate_project("gem-dev-shop")
    assert result["ok"] is True
    assert result["venture_id"] == "gem-dev-shop"
    target = resolve_execution_target()
    assert target["venture_id"] == "gem-dev-shop"
    assert target["source"] == "session"


def test_spoken_project_switch():
    spoken = spoken_project_switch("advoi-system", function_id="fleet_status")
    assert "ADVoi System" in spoken
    assert "Fleet status" in spoken


def test_portfolio_projects_api(client):
    resp = client.get("/api/portfolio/projects")
    assert resp.status_code == 200
    data = resp.json()
    assert "ventures" in data
    assert data["ventures"][0]["functions"]


def test_portfolio_active_api(client):
    resp = client.post(
        "/api/portfolio/active",
        json={"venture_id": "hermes-beacon", "function_id": "memory_health"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["venture_id"] == "hermes-beacon"


def test_filter_squads_for_venture_gem_maps_venture_squad():
    """Mirror filterSquadsForVenture — gem uses venture-squad when present."""

    def filter_squads_for_venture(squads, venture_id, allowed=None):
        if not venture_id:
            return list(squads)
        scoped = [s for s in squads if s.get("venture_id") == venture_id]
        if scoped:
            return scoped
        if allowed:
            allow = set(allowed)
            by_id = [s for s in squads if s.get("id") in allow]
            if by_id:
                return by_id
        fallback = {
            "gem-dev-shop": ["venture-squad", "fleet-squad", "briefs-squad", "review-squad"],
        }.get(venture_id)
        if fallback:
            allow = set(fallback)
            by_fb = [s for s in squads if s.get("id") in allow]
            if by_fb:
                return by_fb
        return list(squads)

    squads = [
        {"id": "fleet-squad", "venture_id": "firstmate-fleet"},
        {"id": "venture-squad", "venture_id": "gem-dev-shop"},
        {"id": "platform-squad", "venture_id": "advoi-system"},
    ]
    gem = filter_squads_for_venture(squads, "gem-dev-shop")
    assert len(gem) == 1
    assert gem[0]["id"] == "venture-squad"
    advoi = filter_squads_for_venture(squads, "advoi-system")
    assert advoi[0]["id"] == "platform-squad"


def test_voice_intent_switch_project(client):
    resp = client.post(
        "/api/voice/intent",
        json={"transcript": "switch to gem dev shop", "preview": False},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == "switch_project"
    assert data["venture_id"] == "gem-dev-shop"


def test_merge_user_features_mirror():
    """Mirror mergeUserFeatures from projectModel.ts."""

    def merge_user_features(venture_functions, user_features, venture_id):
        custom = [
            {"id": row["id"], "label": row["label"], "kind": "custom"}
            for row in user_features
            if row.get("ventureId") == venture_id
        ]
        return list(venture_functions) + custom

    venture_functions = [{"id": "fleet_status", "label": "Fleet", "kind": "frame"}]
    user_features = [{"id": "custom-x", "ventureId": "advoi-system", "label": "Voice UX"}]
    merged = merge_user_features(venture_functions, user_features, "advoi-system")
    assert len(merged) == 2
    assert merged[-1]["kind"] == "custom"


def test_resolve_fleet_project_slug_mirror():
    """Mirror resolveFleetProjectSlug from projectModel.ts."""

    def resolve_fleet_project_slug(active_venture, fleet_profile_slug=None):
        from_bar = (active_venture or {}).get("fleet_slug")
        if from_bar and str(from_bar).strip():
            return str(from_bar).strip()
        from_profile = (fleet_profile_slug or "").strip()
        return from_profile or None

    assert resolve_fleet_project_slug({"fleet_slug": "advoi"}, "clapart") == "advoi"
    assert resolve_fleet_project_slug(None, "clapart") == "clapart"
    assert resolve_fleet_project_slug({"fleet_slug": ""}, None) is None


def test_fleet_action_transcript_mirror():
    """Mirror fleetActionTranscript from projectModel.ts."""

    def fleet_action_transcript(action, project_slug, confirmed=False):
        phrase = action.replace("_", " ")
        scoped = f"{phrase} on {project_slug}" if project_slug else phrase
        return f"{scoped} confirm" if confirmed else scoped

    assert fleet_action_transcript("wake_firstmate", "advoi", True) == "wake firstmate on advoi confirm"
    assert fleet_action_transcript("run_next_backlog", None, False) == "run next backlog"


def test_make_user_feature_id_mirror():
    """Mirror makeUserFeatureId from projectModel.ts."""

    def make_user_feature_id(label: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", label.strip().lower()).strip("-")
        return f"custom-{slug or 'feature'}-abc"

    assert make_user_feature_id("Voice Onboarding").startswith("custom-voice-onboarding-")