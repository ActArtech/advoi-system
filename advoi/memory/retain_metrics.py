"""In-process retain failure metrics (ADR-026 operational visibility).

Counters are process-local: reset on restart. Exposed via
``GET /api/diagnostics/platform`` under ``memory`` (and top-level for convenience).
Never store payload bodies or secrets here — only backend, event_type, and reason.
"""

from __future__ import annotations

import logging
import threading
from typing import Any

_LOGGER = logging.getLogger(__name__)

_lock = threading.Lock()
_retain_failure_count: int = 0
_last_retain_failure: dict[str, Any] | None = None


def record_retain_failure(
    *,
    backend: str,
    event_type: str,
    reason: str,
    detail: str = "",
) -> None:
    """Increment counter and log WARNING with non-secret context."""
    global _retain_failure_count, _last_retain_failure
    safe_reason = (reason or "unknown")[:200]
    safe_detail = (detail or "")[:200]
    # Strip anything that looks like a bearer/api token fragment if it slipped in.
    for secret_marker in ("Bearer ", "api_key=", "Authorization:", "sk-"):
        if secret_marker in safe_detail:
            safe_detail = safe_detail.split(secret_marker)[0].rstrip() + "[redacted]"
        if secret_marker in safe_reason:
            safe_reason = safe_reason.split(secret_marker)[0].rstrip() + "[redacted]"

    with _lock:
        _retain_failure_count += 1
        count = _retain_failure_count
        _last_retain_failure = {
            "backend": backend,
            "event_type": event_type,
            "reason": safe_reason,
        }
        if safe_detail:
            _last_retain_failure["detail"] = safe_detail

    if safe_detail:
        _LOGGER.warning(
            "memory retain failed backend=%s event_type=%s reason=%s detail=%s count=%s",
            backend,
            event_type,
            safe_reason,
            safe_detail,
            count,
        )
    else:
        _LOGGER.warning(
            "memory retain failed backend=%s event_type=%s reason=%s count=%s",
            backend,
            event_type,
            safe_reason,
            count,
        )


def retain_failure_count() -> int:
    with _lock:
        return _retain_failure_count


def last_retain_failure() -> dict[str, Any] | None:
    with _lock:
        return dict(_last_retain_failure) if _last_retain_failure else None


def retain_metrics_snapshot() -> dict[str, Any]:
    """Shape for diagnostics JSON."""
    with _lock:
        last = dict(_last_retain_failure) if _last_retain_failure else None
        return {
            "retain_failure_count": _retain_failure_count,
            "last_retain_failure": last,
        }


def reset_retain_failure_metrics() -> None:
    """Test helper — clear in-process counters."""
    global _retain_failure_count, _last_retain_failure
    with _lock:
        _retain_failure_count = 0
        _last_retain_failure = None


__all__ = [
    "record_retain_failure",
    "retain_failure_count",
    "last_retain_failure",
    "retain_metrics_snapshot",
    "reset_retain_failure_metrics",
]
