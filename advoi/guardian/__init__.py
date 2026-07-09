"""Security, error detection, and recovery (Sentinel)."""

from advoi.guardian.confirmation import (
    evaluate_frame_confirmation,
    frame_needs_confirmation,
    global_confirmation_enabled,
)
from advoi.guardian.recovery import record_agent_failure, record_recovery

__all__ = [
    "evaluate_frame_confirmation",
    "frame_needs_confirmation",
    "global_confirmation_enabled",
    "record_agent_failure",
    "record_recovery",
]