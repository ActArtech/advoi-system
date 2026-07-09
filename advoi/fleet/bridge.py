"""Python entry matching scripts/fm-bridge.sh — forwards to fm-hermes-trigger.sh."""

from __future__ import annotations

import os
from pathlib import Path


def fleet_bridge_script() -> Path | None:
    """Resolve fm-bridge.sh when packaged in the container or repo."""
    explicit = os.getenv("ADVOI_FM_BRIDGE_SCRIPT", "").strip()
    if explicit:
        path = Path(explicit)
        if path.is_file():
            return path
    for candidate in (
        Path("/app/scripts/fm-bridge.sh"),
        Path("scripts/fm-bridge.sh"),
    ):
        if candidate.is_file():
            return candidate
    return None


def fleet_trigger_script() -> Path:
    """Underlying FirstMate trigger (fm-hermes-trigger.sh)."""
    return Path(
        os.getenv(
            "FIRSTMATE_TRIGGER_SCRIPT",
            "/opt/firstmate-fleet/scripts/fm-hermes-trigger.sh",
        )
    )


def resolve_fleet_exec() -> tuple[str, ...]:
    """Return argv prefix: bash + script to invoke with one message argument."""
    bridge = fleet_bridge_script()
    if bridge is not None:
        return ("bash", str(bridge))
    return ("bash", str(fleet_trigger_script()))