"""Ingestion status lifecycle (moat R4 / M7.2–M7.3).

Happy path:
  uploaded → triaged → needs_review → approved → dispatched

Dispatch is allowed only from ``approved``. ``routed`` is retained for
legacy items; ``failed`` is terminal for the MVP state machine.
"""

from __future__ import annotations

from typing import Final

from advoi.ingestion.models import IngestStatus

# Canonical happy-path order (excludes legacy ``routed`` and terminal ``failed``).
HAPPY_PATH: Final[tuple[IngestStatus, ...]] = (
    "uploaded",
    "triaged",
    "needs_review",
    "approved",
    "dispatched",
)

# Explicit allowed transitions. Keys are from-status; values are to-status sets.
ALLOWED_TRANSITIONS: Final[dict[IngestStatus, frozenset[IngestStatus]]] = {
    "uploaded": frozenset({"triaged", "failed"}),
    "triaged": frozenset({"needs_review", "failed"}),
    "needs_review": frozenset({"approved", "triaged", "failed"}),
    # Legacy status from pre-lifecycle MVP: route then review/approve.
    "routed": frozenset({"needs_review", "approved", "failed"}),
    "approved": frozenset({"dispatched", "failed"}),
    "dispatched": frozenset(),
    "failed": frozenset(),
}


class InvalidTransitionError(ValueError):
    """Raised when a status transition is not allowed by the state machine."""

    def __init__(
        self,
        from_status: str,
        to_status: str,
        *,
        item_id: str | None = None,
    ) -> None:
        self.from_status = from_status
        self.to_status = to_status
        self.item_id = item_id
        where = f" for item {item_id}" if item_id else ""
        super().__init__(
            f"Invalid ingestion transition{where}: {from_status!r} → {to_status!r}"
        )


def can_transition(from_status: str, to_status: str) -> bool:
    """Return True if ``from_status`` → ``to_status`` is allowed."""
    allowed = ALLOWED_TRANSITIONS.get(from_status)  # type: ignore[arg-type]
    if allowed is None:
        return False
    return to_status in allowed


def assert_transition(
    from_status: str,
    to_status: str,
    *,
    item_id: str | None = None,
) -> None:
    """Raise ``InvalidTransitionError`` if the transition is illegal."""
    if not can_transition(from_status, to_status):
        raise InvalidTransitionError(from_status, to_status, item_id=item_id)


def transition(
    current: str,
    to_status: IngestStatus,
    *,
    item_id: str | None = None,
) -> IngestStatus:
    """Validate and return the new status."""
    assert_transition(current, to_status, item_id=item_id)
    return to_status


def can_dispatch(status: str) -> bool:
    """Dispatch is only allowed from ``approved``."""
    return status == "approved"
