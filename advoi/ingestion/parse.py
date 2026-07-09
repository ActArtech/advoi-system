"""Extract plain text from uploaded intake files."""

from __future__ import annotations

import json
import os

_TEXT_SUFFIXES = {".txt", ".md", ".markdown", ".json", ".csv", ".log", ".yaml", ".yml"}
_DEFAULT_MAX = 5 * 1024 * 1024


def max_upload_bytes() -> int:
    raw = os.getenv("ADVOI_INGEST_MAX_BYTES", str(_DEFAULT_MAX))
    try:
        return max(1024, int(raw))
    except ValueError:
        return _DEFAULT_MAX


def allowed_suffixes() -> set[str]:
    extra = os.getenv("ADVOI_INGEST_ALLOWED_SUFFIXES", "")
    suffixes = set(_TEXT_SUFFIXES)
    for part in extra.split(","):
        part = part.strip().lower()
        if part.startswith("."):
            suffixes.add(part)
    return suffixes


def extract_text(filename: str, data: bytes) -> str:
    suffix = ""
    if "." in filename:
        suffix = "." + filename.rsplit(".", 1)[-1].lower()

    if suffix not in allowed_suffixes():
        raise ValueError(f"Unsupported file type: {suffix or filename}")

    if len(data) > max_upload_bytes():
        raise ValueError(f"File exceeds limit of {max_upload_bytes()} bytes")

    text = data.decode("utf-8", errors="replace").strip()
    if suffix == ".json":
        try:
            parsed = json.loads(text)
            text = json.dumps(parsed, indent=2)[:120_000]
        except json.JSONDecodeError:
            pass
    return text[:120_000]