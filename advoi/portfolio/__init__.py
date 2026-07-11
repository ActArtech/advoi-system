"""Portfolio control plane — PEL audit trail and Execution Context Registry."""

from advoi.portfolio.ecr import (
    load_execution_context,
    reload_execution_context,
    resolve_execution_target,
)
from advoi.portfolio.gate_snapshot import emit_gate_snapshot_from_report, parse_gate_report
from advoi.portfolio.pel import append_portfolio_event, ensure_portfolio_events_table

__all__ = [
    "append_portfolio_event",
    "ensure_portfolio_events_table",
    "emit_gate_snapshot_from_report",
    "load_execution_context",
    "parse_gate_report",
    "reload_execution_context",
    "resolve_execution_target",
]