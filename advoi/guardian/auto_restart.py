"""Guardian auto-restart — retry failed agent ticks with exponential backoff."""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import Awaitable, Callable
from typing import TypeVar

from advoi.memory.guardian_log import append_guardian_event

_LOGGER = logging.getLogger(__name__)

T = TypeVar("T")


def _max_retries() -> int:
    return int(os.getenv("GUARDIAN_AUTO_RESTART_MAX", "3"))


def _base_delay_secs() -> float:
    return float(os.getenv("GUARDIAN_AUTO_RESTART_BASE_SECS", "5"))


def _max_delay_secs() -> float:
    return float(os.getenv("GUARDIAN_AUTO_RESTART_MAX_SECS", "60"))


def backoff_delay(attempt: int) -> float:
    """Exponential backoff capped at max delay (attempt is 1-based)."""
    delay = _base_delay_secs() * (2 ** (attempt - 1))
    return min(delay, _max_delay_secs())


async def record_restart_attempt(
    agent_id: str,
    attempt: int,
    delay_secs: float,
    *,
    error: str,
) -> bool:
    payload = {
        "agent_id": agent_id,
        "attempt": attempt,
        "delay_secs": delay_secs,
        "error": error,
        "max_retries": _max_retries(),
    }
    _LOGGER.info(
        "guardian auto-restart %s attempt %s/%s in %.1fs",
        agent_id,
        attempt,
        _max_retries(),
        delay_secs,
    )
    return await append_guardian_event("agent_restart_attempt", payload)


async def run_with_auto_restart(
    agent_id: str,
    tick: Callable[[], Awaitable[T]],
    *,
    on_exhausted: Callable[[BaseException], Awaitable[None]] | None = None,
) -> T:
    """Run tick with immediate retries before surfacing failure."""
    max_retries = _max_retries()
    last_exc: BaseException | None = None
    for attempt in range(1, max_retries + 2):
        try:
            return await tick()
        except Exception as exc:
            last_exc = exc
            if attempt > max_retries:
                if on_exhausted:
                    await on_exhausted(exc)
                raise
            delay = backoff_delay(attempt)
            await record_restart_attempt(agent_id, attempt, delay, error=str(exc))
            await asyncio.sleep(delay)
    raise RuntimeError("unreachable") from last_exc