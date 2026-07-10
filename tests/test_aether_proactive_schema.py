"""T0: aether-proactive-latest JSON Schema + gate validator (valid/invalid payloads)."""

from __future__ import annotations

import copy
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from advoi.aether.proactive_schema import (
    DEFAULT_ARTIFACT_PATH,
    DEFAULT_SCHEMA_PATH,
    is_valid_proactive_payload,
    load_schema,
    validate_proactive_file,
    validate_proactive_payload,
)

ROOT = Path(__file__).resolve().parents[1]
AETHER_DOCS = ROOT / "docs" / "aether"
SCHEMA_PATH = AETHER_DOCS / "aether-proactive-latest.schema.json"
ARTIFACT_PATH = AETHER_DOCS / "aether-proactive-latest.json"
FIXTURES = ROOT / "tests" / "fixtures" / "aether-proactive"


def _minimal_valid() -> dict[str, Any]:
    return {
        "project": "/data/projects/advoi",
        "mode": "proactive",
        "findings": [
            {
                "agent": "context",
                "severity": "none",
                "category": "audit",
                "message": "no diff to review",
                "file": "",
            }
        ],
    }


@pytest.fixture
def proactive_schema() -> dict[str, Any]:
    """Loaded JSON Schema for the proactive feed artifact."""
    assert SCHEMA_PATH.is_file(), f"missing schema {SCHEMA_PATH}"
    return load_schema(SCHEMA_PATH)


@pytest.fixture
def proactive_gate_validator(
    proactive_schema: dict[str, Any],
) -> Callable[[Any], list[str]]:
    """Gate validator fixture: returns error list (empty = valid)."""

    def _validate(payload: Any) -> list[str]:
        return validate_proactive_payload(payload, schema=proactive_schema)

    return _validate


@pytest.fixture
def valid_proactive_payload() -> dict[str, Any]:
    """Minimal valid proactive feed payload."""
    return _minimal_valid()


@pytest.fixture
def invalid_proactive_payloads() -> dict[str, dict[str, Any]]:
    """Named invalid payloads covering gate-critical failures."""
    base = _minimal_valid()
    missing_project = copy.deepcopy(base)
    del missing_project["project"]

    empty_findings = copy.deepcopy(base)
    empty_findings["findings"] = []

    bad_mode = copy.deepcopy(base)
    bad_mode["mode"] = "reactive"

    bad_severity = copy.deepcopy(base)
    bad_severity["findings"][0]["severity"] = "urgent"

    missing_finding_fields = copy.deepcopy(base)
    del missing_finding_fields["findings"][0]["message"]

    not_object: Any = ["not", "an", "object"]

    return {
        "missing_project": missing_project,
        "empty_findings": empty_findings,
        "bad_mode": bad_mode,
        "bad_severity": bad_severity,
        "missing_finding_message": missing_finding_fields,
        "not_object": not_object,
    }


# --- schema artifact presence ---


def test_schema_file_exists_and_declares_required():
    assert SCHEMA_PATH.is_file(), f"missing {SCHEMA_PATH}"
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema.get("type") == "object"
    required = set(schema.get("required") or [])
    assert {"project", "mode", "findings"} <= required
    assert "findings" in schema.get("properties", {})
    finding = schema.get("$defs", {}).get("finding") or {}
    assert set(finding.get("required") or []) >= {"agent", "severity", "category", "message"}


def test_default_paths_point_at_docs_aether():
    assert DEFAULT_SCHEMA_PATH == SCHEMA_PATH
    assert DEFAULT_ARTIFACT_PATH == ARTIFACT_PATH


# --- valid payloads ---


def test_valid_minimal_payload(proactive_gate_validator, valid_proactive_payload):
    errors = proactive_gate_validator(valid_proactive_payload)
    assert errors == [], errors
    assert is_valid_proactive_payload(valid_proactive_payload)


def test_valid_actionable_finding(proactive_gate_validator):
    payload = _minimal_valid()
    payload["findings"] = [
        {
            "agent": "governance",
            "severity": "high",
            "category": "decisions",
            "message": "DECISIONS.md missing Priority on open item",
            "file": ".aether/DECISIONS.md",
        }
    ]
    payload["has_high"] = True
    payload["top_severity"] = "high"
    payload["top_summary"] = payload["findings"][0]["message"]
    payload["finding_count"] = 1
    assert proactive_gate_validator(payload) == []


def test_repo_artifact_validates_against_schema(proactive_gate_validator):
    assert ARTIFACT_PATH.is_file(), f"missing {ARTIFACT_PATH}"
    payload = json.loads(ARTIFACT_PATH.read_text(encoding="utf-8"))
    errors = proactive_gate_validator(payload)
    assert errors == [], errors
    assert validate_proactive_file(ARTIFACT_PATH) == []


def test_fixture_valid_file(proactive_gate_validator):
    path = FIXTURES / "valid.json"
    assert path.is_file(), f"missing fixture {path}"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert proactive_gate_validator(payload) == []


# --- invalid payloads ---


@pytest.mark.parametrize(
    "name,expected_substr",
    [
        ("missing_project", "project"),
        ("empty_findings", "minItems"),
        ("bad_mode", "const"),
        ("bad_severity", "enum"),
        ("missing_finding_message", "message"),
        ("not_object", "object"),
    ],
)
def test_invalid_payloads_rejected(
    proactive_gate_validator,
    invalid_proactive_payloads,
    name: str,
    expected_substr: str,
):
    payload = invalid_proactive_payloads[name]
    errors = proactive_gate_validator(payload)
    assert errors, f"expected errors for {name}"
    assert any(expected_substr in e for e in errors), (name, errors)
    assert not is_valid_proactive_payload(payload)


def test_fixture_invalid_files(proactive_gate_validator):
    bad_dir = FIXTURES / "invalid"
    assert bad_dir.is_dir(), f"missing {bad_dir}"
    files = sorted(bad_dir.glob("*.json"))
    assert len(files) >= 3, "expected multiple invalid fixtures"
    for path in files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        errors = proactive_gate_validator(payload)
        assert errors, f"expected invalid: {path.name}"
