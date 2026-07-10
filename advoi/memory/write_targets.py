"""
Explicit memory write targets — no double-write for the same event.

Rule (ADR-026):
  Hindsight  → portfolio facts, governance, cross-project synthesis
  Letta      → agent identity, user prefs, squad operational learning
  Postgres   → structured canonical records (projects, briefs, master-state)
  Redis      → ephemeral turn window + rolling summary only
  Guardian   → error log only (failures ≠ beliefs)
  Never      → Guardian errors → beliefs; fleet backlog → Hindsight / strategic memory
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any


class MemoryTier(str, Enum):
    STRATEGIC = "strategic"
    OPERATIONAL = "operational"
    EPHEMERAL = "ephemeral"


class WriteTarget(str, Enum):
    HINDSIGHT = "hindsight"
    LETTA = "letta"
    POSTGRES = "postgres"
    REDIS = "redis"
    GUARDIAN_LOG = "guardian_log"
    SKIP = "skip"


class MemoryEventType(str, Enum):
    # Strategic → Hindsight (+ Postgres mirror for structured fields)
    PORTFOLIO_FACT = "portfolio_fact"
    GOVERNANCE_DECISION = "governance_decision"
    CROSS_PROJECT_SYNTHESIS = "cross_project_synthesis"
    VENTURE_BELIEF_UPDATE = "venture_belief_update"

    # Operational → Letta (v0.2+) + Postgres; never Hindsight for squad chatter
    SQUAD_LESSON = "squad_lesson"
    USER_PREFERENCE = "user_preference"
    WORKFLOW_EVOLUTION = "workflow_evolution"
    AGENT_IDENTITY = "agent_identity"

    # Structured canonical → Postgres only
    DECISION_BRIEF = "decision_brief"
    PROJECT_STATE = "project_state"
    MASTER_STATE = "master_state"

    # Ephemeral → Redis only
    VOICE_TURN = "voice_turn"
    ROLLING_SUMMARY = "rolling_summary"

    # Failures → Guardian only
    RUNTIME_ERROR = "runtime_error"
    RECOVERY_NOTE = "recovery_note"


# Primary write target per event type (secondary mirrors allowed where noted)
EVENT_WRITE_MAP: dict[MemoryEventType, tuple[WriteTarget, ...]] = {
    MemoryEventType.PORTFOLIO_FACT: (WriteTarget.HINDSIGHT, WriteTarget.POSTGRES),
    MemoryEventType.GOVERNANCE_DECISION: (WriteTarget.HINDSIGHT, WriteTarget.POSTGRES),
    MemoryEventType.CROSS_PROJECT_SYNTHESIS: (WriteTarget.HINDSIGHT,),
    MemoryEventType.VENTURE_BELIEF_UPDATE: (WriteTarget.HINDSIGHT,),
    MemoryEventType.SQUAD_LESSON: (WriteTarget.LETTA, WriteTarget.POSTGRES),
    MemoryEventType.USER_PREFERENCE: (WriteTarget.LETTA,),
    MemoryEventType.WORKFLOW_EVOLUTION: (WriteTarget.LETTA,),
    MemoryEventType.AGENT_IDENTITY: (WriteTarget.LETTA,),
    MemoryEventType.DECISION_BRIEF: (WriteTarget.POSTGRES,),
    MemoryEventType.PROJECT_STATE: (WriteTarget.POSTGRES,),
    MemoryEventType.MASTER_STATE: (WriteTarget.POSTGRES,),
    MemoryEventType.VOICE_TURN: (WriteTarget.REDIS,),
    MemoryEventType.ROLLING_SUMMARY: (WriteTarget.REDIS,),
    MemoryEventType.RUNTIME_ERROR: (WriteTarget.GUARDIAN_LOG,),
    MemoryEventType.RECOVERY_NOTE: (WriteTarget.GUARDIAN_LOG,),
}


def targets_for(event: MemoryEventType) -> tuple[WriteTarget, ...]:
    return EVENT_WRITE_MAP.get(event, (WriteTarget.SKIP,))


def tier_for(event: MemoryEventType) -> MemoryTier:
    if event in (
        MemoryEventType.VOICE_TURN,
        MemoryEventType.ROLLING_SUMMARY,
    ):
        return MemoryTier.EPHEMERAL
    if event in (
        MemoryEventType.PORTFOLIO_FACT,
        MemoryEventType.GOVERNANCE_DECISION,
        MemoryEventType.CROSS_PROJECT_SYNTHESIS,
        MemoryEventType.VENTURE_BELIEF_UPDATE,
    ):
        return MemoryTier.STRATEGIC
    return MemoryTier.OPERATIONAL


# ADR-026 Never-rule: fleet backlog is operational queue state, not strategic memory.
# Match raw backlog dumps and explicit fleet-queue markers — not generic "queued" chatter.
_FLEET_BACKLOG_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"run_next_backlog", re.I),
    re.compile(r"fleet[_\s-]*backlog", re.I),
    re.compile(r"FIRSTMATE_FLEET_PATH", re.I),
    re.compile(r"(?m)^#\s*backlog\b", re.I),
    re.compile(r"(?m)^##\s*(Queued|In flight)\b", re.I),
    re.compile(r"- \[[ xX]\]\s+\*\*[a-z0-9][\w.-]*-0\d+\*\*", re.I),
)


def text_looks_like_fleet_backlog(text: str) -> bool:
    """True when *text* looks like raw fleet backlog (or an explicit fleet-queue marker)."""
    if not text or not text.strip():
        return False
    return any(pat.search(text) for pat in _FLEET_BACKLOG_PATTERNS)


def _payload_text_blobs(payload: dict[str, Any]) -> list[str]:
    """Collect string fields that could carry a backlog dump into Hindsight."""
    blobs: list[str] = []
    for key in ("summary", "text", "content", "body", "spoken_summary", "detail"):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            blobs.append(val)
        elif isinstance(val, dict):
            # Nested spoken/detail from frames may hold file-snapshot backlog.
            for nested in val.values():
                if isinstance(nested, str) and nested.strip():
                    blobs.append(nested)
    # Fallback: stringified payload if no primary fields (retain_strategic uses str(payload)).
    if not blobs:
        blobs.append(str(payload)[:4000])
    return blobs


def payload_has_fleet_backlog(payload: dict[str, Any] | None) -> bool:
    """True when a retain payload contains fleet-backlog-shaped text (ADR-026 never-rule)."""
    if not payload:
        return False
    return any(text_looks_like_fleet_backlog(blob) for blob in _payload_text_blobs(payload))