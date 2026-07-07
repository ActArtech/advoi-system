"""Bridge PWA / data-channel frame triggers into spoken responses."""

from __future__ import annotations

import json
from typing import Any

from advoi.routing.frame_runner import run_frame


async def handle_frame_message(raw: bytes | str) -> str | None:
    """Parse LiveKit data payload; return text to speak or None."""
    try:
        if isinstance(raw, bytes):
            text = raw.decode("utf-8")
        else:
            text = raw
        payload: dict[str, Any] = json.loads(text)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None

    msg_type = payload.get("type")

    if msg_type == "speak":
        text = payload.get("text")
        return str(text).strip() if text else None

    if msg_type != "frame":
        return None

    frame_id = payload.get("frame_id")
    if not frame_id:
        return None

    confirmed = bool(payload.get("confirmed", False))
    refresh = bool(payload.get("refresh", False))
    result = await run_frame(str(frame_id), confirmed=confirmed, refresh=refresh)
    return result.spoken_summary