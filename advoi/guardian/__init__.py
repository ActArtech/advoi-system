"""Security, error detection, and recovery (Sentinel)."""

from advoi.guardian.confirmation import (
    evaluate_fleet_confirmation,
    evaluate_frame_confirmation,
    fleet_action_needs_confirmation,
    fleet_confirmation_prompt,
    frame_needs_confirmation,
    global_confirmation_enabled,
    high_risk_fleet_actions,
)
from advoi.guardian.recovery import record_agent_failure, record_recovery

__all__ = [
    "evaluate_fleet_confirmation",
    "evaluate_frame_confirmation",
    "fleet_action_needs_confirmation",
    "fleet_confirmation_prompt",
    "frame_needs_confirmation",
    "global_confirmation_enabled",
    "high_risk_fleet_actions",
    "record_agent_failure",
    "record_recovery",
]