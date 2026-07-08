"""Uvicorn entrypoint for ADVoi API."""

from __future__ import annotations

import os

import uvicorn


def main() -> None:
    host = os.getenv("ADVOI_API_HOST", "0.0.0.0")
    # Container always listens on ADVOI_API_LISTEN_PORT (default 8000).
    # ADVOI_API_HOST_PORT / ADVOI_API_PORT in deploy/.env is the host bind only.
    port = int(os.getenv("ADVOI_API_LISTEN_PORT", "8000"))
    uvicorn.run(
        "advoi.api.app:app",
        host=host,
        port=port,
        reload=os.getenv("ADVOI_ENV", "development") == "development",
    )


if __name__ == "__main__":
    main()