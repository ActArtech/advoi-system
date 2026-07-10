"""T0: ontology frame/agent validators + API 422 for unknown ids."""

from __future__ import annotations

import pytest

from advoi.ontology import (
    OntologyValidationError,
    require_agent_id,
    require_frame_id,
)
from advoi.ontology.validate import OntologyValidationError as ValidateError


def test_require_frame_id_known():
    assert require_frame_id("fleet_status") == "fleet_status"


def test_require_frame_id_unknown():
    with pytest.raises(OntologyValidationError) as ei:
        require_frame_id("not_a_real_frame")
    exc = ei.value
    assert exc.code == "UNKNOWN_FRAME_ID"
    assert "not_a_real_frame" in exc.detail
    assert exc.field == "frame_id"
    assert exc.as_dict() == {"detail": exc.detail, "code": "UNKNOWN_FRAME_ID"}


def test_require_frame_id_empty():
    with pytest.raises(OntologyValidationError) as ei:
        require_frame_id("")
    assert ei.value.code == "UNKNOWN_FRAME_ID"


def test_require_agent_id_known():
    assert require_agent_id("fleet-scout") == "fleet-scout"


def test_require_agent_id_unknown():
    with pytest.raises(OntologyValidationError) as ei:
        require_agent_id("not-an-agent")
    exc = ei.value
    assert exc.code == "UNKNOWN_AGENT_ID"
    assert "not-an-agent" in exc.detail
    assert exc.as_dict()["code"] == "UNKNOWN_AGENT_ID"


def test_package_export_matches_module():
    assert OntologyValidationError is ValidateError


@pytest.mark.asyncio
async def test_run_frame_unknown_raises_ontology_error():
    from advoi.routing.frame_runner import run_frame

    with pytest.raises(OntologyValidationError) as ei:
        await run_frame("definitely_unknown_frame")
    assert ei.value.code == "UNKNOWN_FRAME_ID"


@pytest.mark.asyncio
async def test_run_frame_known_still_works():
    from advoi.routing.frame_runner import run_frame

    result = await run_frame("fleet_status")
    assert result.frame_id == "fleet_status"
    assert result.agent_id == "fleet-scout"
    assert result.status == "ok"


def test_api_unknown_frame_id_returns_422(client):
    resp = client.post("/api/frames/not_a_real_frame/run", json={})
    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "UNKNOWN_FRAME_ID"
    assert "not_a_real_frame" in body["detail"]
    assert "detail" in body
    # Must not be a bare 500 / nested FastAPI validation list.
    assert not isinstance(body.get("detail"), list)


def test_api_known_frame_id_still_works(client):
    resp = client.post("/api/frames/fleet_status/run", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["frame_id"] == "fleet_status"
    assert data["agent_id"] == "fleet-scout"
    assert data["spoken_summary"]


def test_api_orchestrate_unknown_frame_returns_422(client):
    resp = client.post(
        "/api/agents/orchestrate",
        json={"frame_ids": ["fleet_status", "bogus_frame"]},
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "UNKNOWN_FRAME_ID"
    assert "bogus_frame" in body["detail"]


def test_api_orchestrate_known_frames_still_work(client):
    resp = client.post(
        "/api/agents/orchestrate",
        json={"frame_ids": ["fleet_status", "open_briefs"]},
    )
    assert resp.status_code == 200
    assert len(resp.json()["results"]) == 2
