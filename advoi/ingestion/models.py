"""Ingestion item models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

# Lifecycle (moat R4 / M7): uploaded → triaged → needs_review → approved → dispatched
# ``routed`` retained for legacy MVP items; ``failed`` is terminal.
IngestStatus = Literal[
    "uploaded",
    "triaged",
    "needs_review",
    "routed",
    "approved",
    "dispatched",
    "failed",
]
PriorityBand = Literal["low", "medium", "high"]


@dataclass
class IngestItem:
    id: str
    filename: str
    status: IngestStatus = "uploaded"
    venture_id: str | None = None
    project_slug: str | None = None
    route_confidence: float = 0.0
    priority: PriorityBand = "medium"
    priority_score: int = 50
    dev_recommended: bool = False
    summary: str = ""
    task_hint: str = ""
    content_preview: str = ""
    size_bytes: int = 0
    mime_type: str | None = None
    error: str | None = None
    dispatch_result: dict[str, Any] | None = None
    paperclip_ticket_id: str | None = None
    created_at: float = 0.0
    updated_at: float = 0.0
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
