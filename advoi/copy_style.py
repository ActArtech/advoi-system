"""User-facing copy rules for voice and PWA."""

from __future__ import annotations

import re

_BRIEF_PREFIX = re.compile(r"^open\s+brief:\s*", re.IGNORECASE)


def plain_copy(text: str) -> str:
    """Remove em/en dashes from strings shown or spoken to users."""
    if not text:
        return text
    return text.replace("\u2014", ", ").replace("\u2013", ", ").replace("  ", " ").strip()


def normalize_brief_title(title: str) -> str:
    """Strip redundant 'Open brief:' prefix from stored titles."""
    t = (title or "").strip()
    cleaned = _BRIEF_PREFIX.sub("", t).strip()
    return cleaned or t


def format_briefs_spoken(titles: list[str], *, max_items: int = 3) -> str:
    """Natural TTS line for open briefs (no repeated 'Open brief' noise)."""
    cleaned = [normalize_brief_title(str(t)) for t in titles if t and str(t).strip()]
    if not cleaned:
        return "No open briefs right now."

    shown = cleaned[:max_items]
    n = len(shown)
    if n == 1:
        return f"You have one open brief: {shown[0]}."

    ordinals = ("First", "Second", "Third")
    parts: list[str] = []
    for i, title in enumerate(shown):
        label = ordinals[i] if i < len(ordinals) else "Next"
        parts.append(f"{label}, {title}")
    return f"You have {n} open briefs. " + ". ".join(parts) + "."