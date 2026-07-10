"""Guardian error log — failures are NOT beliefs (ADR-006, ADR-026)."""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from advoi.observability.otel_setup import current_span_id, current_trace_id, otel_enabled

_LOGGER = logging.getLogger(__name__)


def _guardian_log_path() -> Path:
    return Path(os.getenv("GUARDIAN_LOG_PATH", "docs/error-log/guardian-events.jsonl"))


async def append_guardian_event(event_type: str, payload: dict[str, Any]) -> bool:
    """Append one Guardian JSONL record.

    When ``OTEL_ENABLED`` is active, each record includes top-level ``trace_id``
    and ``span_id`` fields (str hex or null) for correlation with OTel / PEL.
    When OTel is disabled the fields are omitted so older consumers stay clean.
    """
    try:
        log_path = _guardian_log_path()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        record: dict[str, Any] = {
            "ts": datetime.now(UTC).isoformat(),
            "event_type": event_type,
            "payload": payload,
        }
        if otel_enabled():
            record["trace_id"] = current_trace_id()
            record["span_id"] = current_span_id()
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
        return True
    except Exception as exc:
        _LOGGER.warning("guardian log write failed: %s", exc)
        return False
