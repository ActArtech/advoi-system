"""HTTP bridge to Hindsight inside Hermes — only service with docker.sock access."""

from __future__ import annotations

import json
import logging
import os
import subprocess
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

_LOGGER = logging.getLogger("advoi.memory.bridge")
app = FastAPI(title="advoi-memory-bridge", version="0.1.0")


class RecallRequest(BaseModel):
    query: str = ""
    limit: int = 8


class RetainRequest(BaseModel):
    event_type: str = "portfolio_fact"
    summary: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)


def _bridge_call(action: str, **kwargs: Any) -> dict[str, Any]:
    cfg_container = os.getenv("HERMES_CONTAINER", "hermes")
    script = os.getenv(
        "HINDSIGHT_BRIDGE_SCRIPT",
        "/vps-projects/advoi/scripts/hindsight-bridge.py",
    )
    payload = json.dumps({"action": action, **kwargs})
    import shutil

    docker_bin = shutil.which("docker") or "/usr/bin/docker"
    proc = subprocess.run(
        [docker_bin, "exec", cfg_container, "python", script, "--json", payload],
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )
    if proc.returncode != 0:
        err = proc.stderr.strip() or proc.stdout.strip() or "bridge failed"
        _LOGGER.warning("hindsight bridge error: %s", err)
        return {"ok": False, "error": err}
    try:
        return json.loads(proc.stdout.strip() or "{}")
    except json.JSONDecodeError:
        return {"ok": False, "error": "invalid bridge json"}


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.post("/recall")
def recall(req: RecallRequest) -> dict[str, Any]:
    return _bridge_call("recall", query=req.query, limit=req.limit)


@app.post("/retain")
def retain(req: RetainRequest) -> dict[str, Any]:
    return _bridge_call(
        "retain",
        event_type=req.event_type,
        summary=req.summary,
        payload=req.payload,
    )


def main() -> None:
    import uvicorn

    port = int(os.getenv("ADVOI_MEMORY_BRIDGE_PORT", "8095"))
    logging.basicConfig(level=os.getenv("ADVOI_LOG_LEVEL", "INFO"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level=os.getenv("ADVOI_LOG_LEVEL", "info").lower())


if __name__ == "__main__":
    main()