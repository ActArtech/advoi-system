"""Guardian auto-restart backoff tests."""

from __future__ import annotations

import pytest

from advoi.guardian.auto_restart import backoff_delay, run_with_auto_restart


def test_backoff_delay_caps():
    assert backoff_delay(1) == 5.0
    assert backoff_delay(2) == 10.0
    assert backoff_delay(10) == 60.0


@pytest.mark.asyncio
async def test_retries_then_succeeds(monkeypatch, tmp_path):
    monkeypatch.setenv("GUARDIAN_LOG_PATH", str(tmp_path / "g.jsonl"))
    monkeypatch.setenv("GUARDIAN_AUTO_RESTART_MAX", "2")
    monkeypatch.setenv("GUARDIAN_AUTO_RESTART_BASE_SECS", "0.01")

    calls = {"n": 0}

    async def flaky() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("transient")
        return "ok"

    result = await run_with_auto_restart("fleet-scout", flaky)
    assert result == "ok"
    assert calls["n"] == 3


@pytest.mark.asyncio
async def test_exhausted_calls_handler(monkeypatch, tmp_path):
    monkeypatch.setenv("GUARDIAN_LOG_PATH", str(tmp_path / "g.jsonl"))
    monkeypatch.setenv("GUARDIAN_AUTO_RESTART_MAX", "1")
    monkeypatch.setenv("GUARDIAN_AUTO_RESTART_BASE_SECS", "0.01")

    seen: list[str] = []

    async def always_fail() -> None:
        raise ValueError("persistent")

    async def on_exhausted(exc: BaseException) -> None:
        seen.append(str(exc))

    with pytest.raises(ValueError, match="persistent"):
        await run_with_auto_restart(
            "brief-curator",
            always_fail,
            on_exhausted=on_exhausted,
        )
    assert seen == ["persistent"]