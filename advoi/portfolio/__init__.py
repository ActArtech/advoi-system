"""Portfolio control plane — PEL audit trail and Execution Context Registry."""

from advoi.portfolio.ecr import (
    clear_session_active_venture,
    load_execution_context,
    reload_execution_context,
    resolve_execution_target,
    set_session_active_venture,
)
from advoi.portfolio.projects import (
    activate_project,
    build_projects_catalog,
    classify_project_voice_intent,
    match_venture_id,
)
from advoi.portfolio.gate_snapshot import emit_gate_snapshot_from_report, parse_gate_report
from advoi.portfolio.pel import append_portfolio_event, ensure_portfolio_events_table

__all__ = [
    "activate_project",
    "append_portfolio_event",
    "build_projects_catalog",
    "classify_project_voice_intent",
    "clear_session_active_venture",
    "ensure_portfolio_events_table",
    "emit_gate_snapshot_from_report",
    "load_execution_context",
    "match_venture_id",
    "parse_gate_report",
    "reload_execution_context",
    "resolve_execution_target",
    "set_session_active_venture",
]