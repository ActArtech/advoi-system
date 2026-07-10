"""fm-bridge invoke idempotency (60s dedupe window).

Contract (ops / clients)
------------------------
Duplicate fleet trigger invokes that share the same idempotency key within
``ADVOI_FLEET_IDEMPOTENCY_WINDOW_SECS`` (default **60**) return the **same
result** without re-executing ``fm-bridge.sh`` / ``fm-hermes-trigger.sh``.

**How to pass the key** (first non-empty wins):

1. HTTP header: ``Idempotency-Key: <opaque-string>``
2. JSON body field: ``idempotency_key`` on ``POST /api/fleet/trigger``
3. Keyword arg: ``idempotency_key=`` on ``invoke_fleet_trigger`` /
   ``fleet_trigger_from_voice`` (internal / tests)

**Key rules**

- Opaque client-chosen string (UUID recommended). Max length 256 after strip.
- Empty / whitespace-only keys are ignored (no dedupe).
- Scope is process-local in-memory (single API worker). Not shared across
  multi-replica deploys unless a future Redis backend is added.
- Only terminal dispatch results are cached. ``confirmation_required`` is
  never stored so a later ``confirmed=true`` with the same key still runs.
- Replay responses include ``deduped: true`` and ``idempotency_key``.

**Example**

.. code-block:: bash

   curl -X POST "$API/api/fleet/trigger" \\
     -H "Content-Type: application/json" \\
     -H "Idempotency-Key: arm-clapart-$(date +%s)" \\
     -d '{"action":"wake_firstmate","confirmed":true,"project":"clapart"}'
"""

from __future__ import annotations

import copy
import os
import time
from typing import Any

# Default window matching task contract (moat: no duplicate fleet dispatch).
DEFAULT_WINDOW_SECS = 60
MAX_KEY_LEN = 256

# key -> (expires_at_monotonic, result)
_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}


def idempotency_window_secs() -> float:
    raw = os.getenv("ADVOI_FLEET_IDEMPOTENCY_WINDOW_SECS", "").strip()
    if not raw:
        return float(DEFAULT_WINDOW_SECS)
    try:
        return max(0.0, float(raw))
    except ValueError:
        return float(DEFAULT_WINDOW_SECS)


def normalize_idempotency_key(key: str | None) -> str | None:
    """Return a usable key or None when absent/invalid."""
    if key is None:
        return None
    text = str(key).strip()
    if not text or len(text) > MAX_KEY_LEN:
        return None
    return text


def clear_idempotency_cache() -> None:
    """Drop all cached invoke results (tests only)."""
    _CACHE.clear()


def _purge_expired(now: float | None = None) -> None:
    t = time.monotonic() if now is None else now
    expired = [k for k, (exp, _) in _CACHE.items() if exp <= t]
    for k in expired:
        _CACHE.pop(k, None)


def get_idempotent_result(key: str | None) -> dict[str, Any] | None:
    """Return a deep copy of a cached terminal result if still within window."""
    normalized = normalize_idempotency_key(key)
    if not normalized:
        return None
    now = time.monotonic()
    _purge_expired(now)
    entry = _CACHE.get(normalized)
    if not entry:
        return None
    exp, payload = entry
    if exp <= now:
        _CACHE.pop(normalized, None)
        return None
    result = copy.deepcopy(payload)
    result["deduped"] = True
    result["idempotency_key"] = normalized
    return result


def store_idempotent_result(key: str | None, result: dict[str, Any]) -> None:
    """Cache a terminal dispatch result for the configured window.

    Skips non-terminal statuses such as ``confirmation_required``.
    """
    normalized = normalize_idempotency_key(key)
    if not normalized:
        return
    status = str(result.get("status") or "")
    if status == "confirmation_required":
        return
    window = idempotency_window_secs()
    if window <= 0:
        return
    now = time.monotonic()
    _purge_expired(now)
    # Store without replay flags so the original response shape is preserved.
    payload = copy.deepcopy(result)
    payload.pop("deduped", None)
    payload["idempotency_key"] = normalized
    _CACHE[normalized] = (now + window, payload)
