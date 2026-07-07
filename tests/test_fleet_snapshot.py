"""Fleet status file-snapshot tests (no docker / mock)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from advoi.routing import frame_runner  # noqa: E402


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