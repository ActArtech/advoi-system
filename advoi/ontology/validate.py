"""Ontology id validators — raise structured errors for unregistered ids.

Membership checks use ``advoi.ontology.registry``. HTTP mapping (422) lives in
the API composition root; this module stays FastAPI-free.
"""

from __future__ import annotations

from advoi.ontology.registry import (
    is_valid_agent_id,
    is_valid_frame_id,
    is_valid_venture_id,
)


class OntologyValidationError(Exception):
    """Unregistered ontology identifier (frame_id / agent_id / venture_id / …)."""

    def __init__(self, detail: str, *, code: str, field: str | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.code = code
        self.field = field

    def as_dict(self) -> dict[str, str]:
        """Structured body for HTTP 422: ``{detail, code}``."""
        return {"detail": self.detail, "code": self.code}


def require_frame_id(frame_id: str) -> str:
    """Return frame_id if registered; else raise OntologyValidationError."""
    if not frame_id or not is_valid_frame_id(frame_id):
        raise OntologyValidationError(
            f"Unknown frame_id: {frame_id!r}",
            code="UNKNOWN_FRAME_ID",
            field="frame_id",
        )
    return frame_id


def require_agent_id(agent_id: str) -> str:
    """Return agent_id if registered; else raise OntologyValidationError."""
    if not agent_id or not is_valid_agent_id(agent_id):
        raise OntologyValidationError(
            f"Unknown agent_id: {agent_id!r}",
            code="UNKNOWN_AGENT_ID",
            field="agent_id",
        )
    return agent_id


def require_venture_id(venture_id: str) -> str:
    """Return venture_id if registered; else raise OntologyValidationError."""
    if not venture_id or not is_valid_venture_id(venture_id):
        raise OntologyValidationError(
            f"Unknown venture_id: {venture_id!r}",
            code="UNKNOWN_VENTURE_ID",
            field="venture_id",
        )
    return venture_id
