"""
Memory router — recall before turns, retain after, routed by ADR-026 write targets.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any

from advoi.memory.write_targets import (
    MemoryEventType,
    MemoryTier,
    WriteTarget,
    targets_for,
    tier_for,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class MemoryConfig:
    provider: str = "hindsight"
    hermes_container: str = "hermes"
    hindsight_enabled: bool = True
    letta_enabled: bool = False
    letta_base_url: str = ""
    letta_agent_id: str = "advoi-executive"
    database_url: str = ""
    redis_url: str = ""


@dataclass
class RecallResult:
    strategic: list[dict[str, Any]] = field(default_factory=list)
    operational: list[dict[str, Any]] = field(default_factory=list)
    ephemeral: list[dict[str, Any]] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)


def load_memory_config() -> MemoryConfig:
    provider = os.getenv("MEMORY_PROVIDER", "hindsight").lower()
    return MemoryConfig(
        provider=provider,
        hermes_container=os.getenv("HERMES_CONTAINER", "hermes"),
        hindsight_enabled=provider in ("hindsight", "both"),
        letta_enabled=os.getenv("LETTA_ENABLED", "false").lower() == "true",
        letta_base_url=os.getenv("LETTA_BASE_URL", "http://letta:8283"),
        letta_agent_id=os.getenv("LETTA_AGENT_ID", "advoi-executive"),
        database_url=os.getenv("DATABASE_URL", ""),
        redis_url=os.getenv("REDIS_URL", ""),
    )


class MemoryRouter:
    def __init__(self, cfg: MemoryConfig | None = None):
        self.cfg = cfg or load_memory_config()

    async def recall(
        self,
        *,
        session_id: str,
        query: str,
        tiers: tuple[MemoryTier, ...] | None = None,
    ) -> RecallResult:
        """Recall before each voice/orchestration turn."""
        want = set(tiers or (MemoryTier.STRATEGIC, MemoryTier.OPERATIONAL, MemoryTier.EPHEMERAL))
        result = RecallResult()

        if MemoryTier.EPHEMERAL in want and self.cfg.redis_url:
            from advoi.memory.redis_store import recall_ephemeral

            result.ephemeral = await recall_ephemeral(session_id)
            result.sources.append("redis")

        if MemoryTier.STRATEGIC in want and self.cfg.hindsight_enabled:
            from advoi.memory.hindsight import recall_strategic

            result.strategic = await recall_strategic(query, hermes_container=self.cfg.hermes_container)
            result.sources.append("hindsight")

        if MemoryTier.OPERATIONAL in want:
            from advoi.memory.operational_bridge import recall_operational_unified

            rows, source = await recall_operational_unified(query)
            result.operational = rows
            if source != "none":
                result.sources.append(source)

        return result

    async def retain(
        self,
        event_type: MemoryEventType,
        payload: dict[str, Any],
        *,
        session_id: str | None = None,
    ) -> dict[str, bool]:
        """Retain after turn — routes to explicit targets only."""
        targets = targets_for(event_type)
        tier = tier_for(event_type)
        results: dict[str, bool] = {}

        _LOGGER.debug("retain %s tier=%s targets=%s", event_type.value, tier.value, targets)

        for target in targets:
            if target == WriteTarget.SKIP:
                continue
            if target == WriteTarget.HINDSIGHT and self.cfg.hindsight_enabled:
                from advoi.memory.hindsight import retain_strategic
                from advoi.memory.write_targets import payload_has_fleet_backlog

                # ADR-026 Never-rule: fleet backlog must never hit Hindsight.
                if payload_has_fleet_backlog(payload):
                    _LOGGER.warning(
                        "retain blocked hindsight: fleet backlog payload (event=%s)",
                        event_type.value,
                    )
                    results["hindsight"] = False
                    continue

                results["hindsight"] = await retain_strategic(
                    event_type.value, payload, hermes_container=self.cfg.hermes_container
                )
            elif target == WriteTarget.LETTA:
                from advoi.memory.operational_bridge import retain_operational_unified

                bridge = await retain_operational_unified(event_type.value, payload)
                results.update(bridge)
            elif target == WriteTarget.POSTGRES and self.cfg.database_url:
                from advoi.memory.postgres_store import retain_structured

                results["postgres"] = await retain_structured(event_type.value, payload)
            elif target == WriteTarget.REDIS and self.cfg.redis_url and session_id:
                from advoi.memory.redis_store import retain_ephemeral

                results["redis"] = await retain_ephemeral(session_id, payload)
            elif target == WriteTarget.GUARDIAN_LOG:
                from advoi.memory.guardian_log import append_guardian_event

                results["guardian_log"] = await append_guardian_event(event_type.value, payload)

        return results