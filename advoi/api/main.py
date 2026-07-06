"""Uvicorn entrypoint for ADVoi API."""

from __future__ import annotations

import os

import uvicorn


def main() -> None:
    host = os.getenv("ADVOI_API_HOST", "0.0.0.0")
    port = int(os.getenv("ADVOI_API_PORT", "8000"))
    uvicorn.run(
        "advoi.api.app:app",
        host=host,
        port=port,
        reload=os.getenv("ADVOI_ENV", "development") == "development",
    )


if __name__ == "__main__":
    main()