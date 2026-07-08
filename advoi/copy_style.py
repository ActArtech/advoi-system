"""User-facing copy rules for voice and PWA."""

from __future__ import annotations


def plain_copy(text: str) -> str:
    """Remove em/en dashes from strings shown or spoken to users."""
    if not text:
        return text
    return text.replace("\u2014", ", ").replace("\u2013", ", ").replace("  ", " ").strip()