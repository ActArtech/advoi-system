#!/usr/bin/env python3
"""Generate minimal ADVoi PWA icons (solid brand color)."""
from __future__ import annotations

import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "web" / "public"
# slate-900 #0f172a
RGBA = (15, 23, 42, 255)


def _png(size: int) -> bytes:
    raw = b""
    row = bytes(RGBA) * size
    for _ in range(size):
        raw += b"\x00" + row
    compressed = zlib.compress(raw, 9)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", compressed)
        + chunk(b"IEND", b"")
    )


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    for size in (192, 512):
        path = ROOT / f"icon-{size}.png"
        path.write_bytes(_png(size))
        print(f"wrote {path}")


if __name__ == "__main__":
    main()