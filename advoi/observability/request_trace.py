"""HTTP request tracing — correlation ID and latency headers."""

from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_LOGGER = logging.getLogger("advoi.request")

_SKIP_LOG_SUFFIXES = ("/health", "/api/health")


class RequestTraceMiddleware(BaseHTTPMiddleware):
    """Attach request id and response time; log non-health traffic."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = (request.headers.get("x-request-id") or "").strip() or uuid.uuid4().hex[:12]
        started = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
        path = request.url.path
        response.headers["x-request-id"] = request_id
        response.headers["x-response-time-ms"] = str(elapsed_ms)
        if not any(path.endswith(suffix) for suffix in _SKIP_LOG_SUFFIXES):
            _LOGGER.info(
                "request method=%s path=%s status=%s ms=%s id=%s",
                request.method,
                path,
                response.status_code,
                elapsed_ms,
                request_id,
            )
        return response