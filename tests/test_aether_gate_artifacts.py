"""T0: fm-aether-gate feed artifacts under docs/aether/ must exist and parse."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AETHER_DOCS = ROOT / "docs" / "aether"
PROACTIVE_JSON = AETHER_DOCS / "aether-proactive-latest.json"
DIRECTIVES_MD = AETHER_DOCS / "AETHER-DIRECTIVES.md"


def test_aether_proactive_latest_json_exists_and_parses():
    assert PROACTIVE_JSON.is_file(), f"missing {PROACTIVE_JSON}"
    payload = json.loads(PROACTIVE_JSON.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    project = str(payload.get("project", ""))
    assert "advoi" in project.replace("\\", "/"), f"project must reference advoi: {project!r}"
    findings = payload.get("findings")
    assert isinstance(findings, list), "findings must be a list"
    assert len(findings) >= 1, "findings must be non-empty for gate feed"


def test_aether_directives_md_exists_with_required_markers():
    assert DIRECTIVES_MD.is_file(), f"missing {DIRECTIVES_MD}"
    text = DIRECTIVES_MD.read_text(encoding="utf-8")
    assert "Generated **" in text, "directives must include Generated **timestamp**"
    assert "## Findings" in text, "directives must include ## Findings section"
    assert "advoi" in text, "directives must reference advoi venture path"
    assert "| Top finding |" in text, "directives must include Top finding table row"
