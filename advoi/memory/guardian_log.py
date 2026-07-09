"""Guardian error log — failures are NOT beliefs (ADR-006, ADR-026)."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_LOGGER = logging.getLogger(__name__)


def _guardian_log_path() -> Path:
    return Path(os.getenv("GUARDIAN_LOG_PATH", "docs/error-log/guardian-events.jsonl"))


async def append_guardian_event(event_type: str, payload: dict[str, Any]) -> bool:
    try:
        log_path = _guardian_log_path()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "payload": payload,
        }
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
        return True
    except Exception as exc:
        _LOGGER.warning("guardian log write failed: %s", exc)
        return False