"""
Explicit memory write targets — no double-write for the same event.

Rule (ADR-026):
  Hindsight  → portfolio facts, governance, cross-project synthesis
  Letta      → agent identity, user prefs, squad operational learning
  Postgres   → structured canonical records (projects, briefs, master-state)
  Redis      → ephemeral turn window + rolling summary only
  Guardian   → error log only (failures ≠ beliefs)
"""

from __future__ import annotations

from enum import Enum


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