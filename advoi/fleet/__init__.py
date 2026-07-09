"""FirstMate fleet bridge — voice/API triggers via fm-hermes-trigger.sh."""

from advoi.fleet.trigger import (
    fleet_trigger_from_voice,
    invoke_fleet_trigger,
    next_backlog_item,
    peek_fleet_backlog,
    resolve_active_project,
)

__all__ = [
    "fleet_trigger_from_voice",
    "invoke_fleet_trigger",
    "next_backlog_item",
    "peek_fleet_backlog",
    "resolve_active_project",
]