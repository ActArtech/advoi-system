"""Fleet status file-snapshot tests (no docker / mock)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from advoi.portfolio.ecr import clear_session_active_venture
from advoi.routing import frame_runner  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_session_override():
    """Fleet scope reads ECR session; never leak into other test modules."""
    clear_session_active_venture()
    yield
    clear_session_active_venture()


@pytest.fixture
def fleet_tree(tmp_path: Path) -> Path:
    root = tmp_path / "fleet"
    data = root / "data"
    state = root / "state"
    (data / "config").mkdir(parents=True)
    state.mkdir(parents=True)

    (data / "config" / "fleet-profile.md").write_text(
        "active_slug: clapart\ngithub_repo: ActArtech/clapart\n",
        encoding="utf-8",
    )
    (data / "backlog.md").write_text(
        """# backlog

## In flight
_(none)_

## Queued
- [ ] **fe-redirect-external-01** - Off-topic handoff
- [ ] **fe-relief-checkin-01** - Relief prompt
""",
        encoding="utf-8",
    )
    (state / ".afk").write_text("1", encoding="utf-8")
    (state / ".wake-queue").write_bytes(b"x" * 42)
    return root


def test_collect_fleet_snapshot_from_disk(fleet_tree: Path):
    spoken, detail = frame_runner._collect_fleet_snapshot_from_disk(fleet_tree)
    assert spoken is not None
    assert "clapart" in spoken
    assert "Nothing in flight" in spoken
    assert "2 queued" in spoken
    assert detail["source"] == "file_snapshot"
    assert detail["state"]["afk_on"] is True
    assert detail["state"]["wake_queue_bytes"] == 42


def test_session_scope_overrides_profile_slug(fleet_tree: Path, monkeypatch: pytest.MonkeyPatch):
    """Project bar session must win over fleet-profile.md active_slug."""
    from advoi.portfolio.ecr import clear_session_active_venture, set_session_active_venture

    # Mixed backlog: profile is clapart, session will be gem-dev-shop.
    data = fleet_tree / "data"
    (data / "backlog.md").write_text(
        """# backlog

## In flight
_(none)_

## Queued
- [ ] **advoi-ops-01** - ADVoi only (repo: advoi, value: 8, complexity: S)
- [ ] **gem-fe-01** - Gem only (repo: gem-dev-shop, value: 7, complexity: S)
- [ ] **clapart-fe-01** - Clapart only (repo: clapart, value: 6, complexity: S)
""",
        encoding="utf-8",
    )
    (data / "feedback-backlog-gem-dev-shop.md").write_text(
        """# feedback gem

## Queued
- [ ] **fe-aether-intake-01** - Review intake (repo: gem-dev-shop, value: 7)
""",
        encoding="utf-8",
    )

    clear_session_active_venture()
    set_session_active_venture("gem-dev-shop")
    try:
        spoken, detail = frame_runner._collect_fleet_snapshot_from_disk(fleet_tree)
    finally:
        clear_session_active_venture()

    assert "gem-dev-shop" in spoken
    assert "clapart" not in spoken.lower() or "Fleet snapshot for gem-dev-shop" in spoken
    assert detail["active_slug"] == "gem-dev-shop"
    assert detail["scope_source"] == "session"
    assert detail.get("profile_active_slug") == "clapart"
    queued = detail["backlog"]["queued_full"]
    assert "fe-aether-intake-01" in queued
    assert "gem-fe-01" in queued
    assert "advoi-ops-01" not in queued
    assert "clapart-fe-01" not in queued


def test_without_session_keeps_profile_slug(fleet_tree: Path):
    from advoi.portfolio.ecr import clear_session_active_venture

    clear_session_active_venture()
    spoken, detail = frame_runner._collect_fleet_snapshot_from_disk(fleet_tree)
    assert "clapart" in spoken
    assert detail["active_slug"] == "clapart"
    assert detail["scope_source"] == "profile"


@pytest.mark.asyncio
async def test_run_fleet_frame_file_snapshot(fleet_tree: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ADVOI_FRAME_MOCK", "false")
    monkeypatch.setenv("FIRSTMATE_FLEET_PATH", str(fleet_tree))
    spoken, detail, status = await frame_runner._run_fleet_scout()
    assert status == "ok"
    assert "clapart" in spoken
    assert detail["source"] == "file_snapshot"
    assert "container" not in spoken.lower()


def test_cached_frame_ignores_docker_error():
    fake_client = MagicMock()
    fake_client.get.return_value = json.dumps(
        {
            "frame_id": "fleet_status",
            "agent_id": "fleet-scout",
            "status": "ok",
            "spoken_summary": "ERROR: container firstmate-fleet not running",
        }
    )
    fake_redis = MagicMock()
    fake_redis.from_url.return_value = fake_client
    with patch.dict("sys.modules", {"redis": fake_redis}):
        assert frame_runner._cached_frame("fleet-scout") is None