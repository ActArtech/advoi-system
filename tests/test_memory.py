"""Memory routing tests — ADR-026 write targets."""

import pytest

from advoi.memory.router import MemoryConfig, MemoryRouter
from advoi.memory.write_targets import (
    MemoryEventType,
    MemoryTier,
    WriteTarget,
    targets_for,
    tier_for,
)


@pytest.mark.parametrize(
    ("event", "expected"),
    [
        (MemoryEventType.PORTFOLIO_FACT, (WriteTarget.HINDSIGHT, WriteTarget.POSTGRES)),
        (MemoryEventType.USER_PREFERENCE, (WriteTarget.LETTA,)),
        (MemoryEventType.VOICE_TURN, (WriteTarget.REDIS,)),
        (MemoryEventType.RUNTIME_ERROR, (WriteTarget.GUARDIAN_LOG,)),
    ],
)
def test_write_targets_no_double_write(event, expected):
    assert targets_for(event) == expected
    assert WriteTarget.HINDSIGHT not in targets_for(MemoryEventType.SQUAD_LESSON) or WriteTarget.LETTA in targets_for(
        MemoryEventType.SQUAD_LESSON
    )


def test_tier_mapping():
    assert tier_for(MemoryEventType.PORTFOLIO_FACT) == MemoryTier.STRATEGIC
    assert tier_for(MemoryEventType.SQUAD_LESSON) == MemoryTier.OPERATIONAL
    assert tier_for(MemoryEventType.VOICE_TURN) == MemoryTier.EPHEMERAL


@pytest.mark.asyncio
async def test_router_retain_skips_when_disabled(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    cfg = MemoryConfig(hindsight_enabled=False, letta_enabled=False)
    router = MemoryRouter(cfg)
    results = await router.retain(
        MemoryEventType.PORTFOLIO_FACT,
        {"summary": "test"},
    )
    assert results == {}