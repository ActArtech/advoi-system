"""Keyword/heuristic triage classifier for ingestion items (M7.2).

Scores route metadata + content preview and recommends a lifecycle target:

- ``triaged`` — routing looks clear; item is classified and ready for the
  human/queue path (still no auto-approve / auto-dispatch).
- ``needs_review`` — low confidence, missing route, urgent, or review-flagged
  content; advance into the review inbox.

This is intentionally heuristic (not an LLM). Full Phase 2 triage UI is out of
scope; see ``advoi/ingestion/README.md``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from advoi.ingestion.models import IngestItem, IngestStatus

TriageTarget = Literal["triaged", "needs_review"]

# Route confidence below this forces human review.
LOW_ROUTE_CONFIDENCE = 0.4
# At or above this, route is treated as clear (unless other flags fire).
HIGH_ROUTE_CONFIDENCE = 0.7
# Content shorter than this is treated as thin / hard to classify.
MIN_PREVIEW_CHARS = 24
# priority_score from route.py high band is 85; treat >= this as urgent.
URGENT_PRIORITY_SCORE = 80

_REVIEW_KEYWORDS: tuple[str, ...] = (
    "needs review",
    "please review",
    "for review",
    "legal",
    "compliance",
    "confidential",
    "security incident",
    "pii",
    "gdpr",
    "approval needed",
    "sign-off",
    "sign off",
    "escalate",
    "human review",
)

_AMBIGUITY_KEYWORDS: tuple[str, ...] = (
    "todo",
    "tbd",
    "unclear",
    "not sure",
    "???",
    "wip",
    "placeholder",
    "fill in",
    "unknown project",
)

_URGENT_KEYWORDS: tuple[str, ...] = (
    "urgent",
    "p0",
    "critical",
    "blocker",
    "asap",
    "production down",
    "sev0",
    "sev1",
)


@dataclass(frozen=True)
class TriageResult:
    """Classifier output for one ingestion item."""

    target_status: TriageTarget
    score: float
    reasons: tuple[str, ...] = ()
    labels: tuple[str, ...] = ()
    signals: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _haystack(
    *,
    content_preview: str,
    summary: str,
    filename: str,
    text: str | None,
) -> str:
    parts = [filename or "", summary or "", content_preview or ""]
    if text:
        parts.append(text)
    return "\n".join(parts).lower()


def _matched_keywords(haystack: str, keywords: tuple[str, ...]) -> list[str]:
    return [k for k in keywords if k in haystack]


def classify_from_signals(
    *,
    route_confidence: float = 0.0,
    priority: str = "medium",
    priority_score: int = 50,
    dev_recommended: bool = False,
    project_slug: str | None = None,
    venture_id: str | None = None,
    content_preview: str = "",
    summary: str = "",
    filename: str = "",
    text: str | None = None,
) -> TriageResult:
    """Score route metadata + content and pick ``triaged`` or ``needs_review``.

    Rules (first matching force-flags win toward ``needs_review``; otherwise
    clear routes land on ``triaged``):

    1. Missing ``project_slug`` → needs_review (``missing_project``)
    2. ``route_confidence`` < :data:`LOW_ROUTE_CONFIDENCE` → needs_review
    3. Empty/thin content preview → needs_review (``thin_content``)
    4. High priority / urgent keywords → needs_review (``urgent``)
    5. Review/legal/compliance keywords → needs_review (``review_flag``)
    6. Ambiguity keywords (todo/tbd/unclear) → needs_review (``ambiguous``)
    7. Otherwise → triaged when route looks usable
    """
    conf = max(0.0, min(1.0, float(route_confidence or 0.0)))
    preview = (content_preview or summary or "").strip()
    hay = _haystack(
        content_preview=content_preview,
        summary=summary,
        filename=filename,
        text=text,
    )

    reasons: list[str] = []
    labels: list[str] = []
    force_review = False

    # Base score from route confidence (0–1).
    score = conf

    if not project_slug:
        force_review = True
        labels.append("missing_project")
        reasons.append("No project_slug on route metadata")
        score -= 0.35
    else:
        labels.append("has_project")
        score += 0.05

    if venture_id:
        labels.append("has_venture")
        score += 0.05
    else:
        labels.append("no_venture")
        score -= 0.05

    if conf < LOW_ROUTE_CONFIDENCE:
        force_review = True
        labels.append("low_confidence")
        reasons.append(
            f"Route confidence {conf:.2f} below threshold {LOW_ROUTE_CONFIDENCE}"
        )
        score -= 0.2
    elif conf >= HIGH_ROUTE_CONFIDENCE:
        labels.append("high_confidence")
        reasons.append(f"Route confidence {conf:.2f} is clear")
        score += 0.1

    if len(preview) < MIN_PREVIEW_CHARS:
        force_review = True
        labels.append("thin_content")
        reasons.append(
            f"Content preview shorter than {MIN_PREVIEW_CHARS} characters"
        )
        score -= 0.25

    urgent_hits = _matched_keywords(hay, _URGENT_KEYWORDS)
    high_priority = priority == "high" or int(priority_score or 0) >= URGENT_PRIORITY_SCORE
    if high_priority or urgent_hits:
        force_review = True
        labels.append("urgent")
        if urgent_hits:
            reasons.append(f"Urgent keywords: {', '.join(urgent_hits[:4])}")
        else:
            reasons.append(f"High priority band (score={priority_score})")
        score -= 0.1

    review_hits = _matched_keywords(hay, _REVIEW_KEYWORDS)
    if review_hits:
        force_review = True
        labels.append("review_flag")
        reasons.append(f"Review keywords: {', '.join(review_hits[:4])}")
        score -= 0.15

    ambiguity_hits = _matched_keywords(hay, _AMBIGUITY_KEYWORDS)
    if ambiguity_hits:
        force_review = True
        labels.append("ambiguous")
        reasons.append(f"Ambiguity keywords: {', '.join(ambiguity_hits[:4])}")
        score -= 0.15

    if dev_recommended:
        labels.append("dev_recommended")
        # Dev work is fine to leave at triaged when route is clear; only a signal.
        score += 0.02

    score = max(0.0, min(1.0, round(score, 3)))

    if force_review:
        target: TriageTarget = "needs_review"
        if not reasons:
            reasons.append("Classifier flags require human review")
    else:
        target = "triaged"
        reasons.append("Route and content look clear enough for triaged")

    signals = {
        "route_confidence": conf,
        "priority": priority,
        "priority_score": int(priority_score or 0),
        "dev_recommended": bool(dev_recommended),
        "project_slug": project_slug,
        "venture_id": venture_id,
        "preview_chars": len(preview),
        "low_route_threshold": LOW_ROUTE_CONFIDENCE,
        "high_route_threshold": HIGH_ROUTE_CONFIDENCE,
    }

    return TriageResult(
        target_status=target,
        score=score,
        reasons=tuple(reasons),
        labels=tuple(dict.fromkeys(labels)),  # stable unique order
        signals=signals,
    )


def classify_item(item: IngestItem, *, text: str | None = None) -> TriageResult:
    """Classify an :class:`IngestItem` from its route fields + content preview."""
    return classify_from_signals(
        route_confidence=item.route_confidence,
        priority=item.priority,
        priority_score=item.priority_score,
        dev_recommended=item.dev_recommended,
        project_slug=item.project_slug,
        venture_id=item.venture_id,
        content_preview=item.content_preview,
        summary=item.summary,
        filename=item.filename,
        text=text,
    )


def apply_triage_result(item: IngestItem, result: TriageResult) -> IngestItem:
    """Persist classifier output on ``item.extra['triage']`` (no status change)."""
    extra = dict(item.extra or {})
    extra["triage"] = result.to_dict()
    item.extra = extra
    return item


def target_status_for_item(item: IngestItem, *, text: str | None = None) -> IngestStatus:
    """Convenience: return classifier target status for an item."""
    return classify_item(item, text=text).target_status
