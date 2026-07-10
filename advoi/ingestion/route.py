"""Route ingested documents to portfolio ventures and FirstMate project slugs."""

from __future__ import annotations

import re
from typing import Any

from advoi.aether.portfolio import VENTURES
from advoi.fleet.trigger import resolve_active_project
from advoi.portfolio.ecr import resolve_execution_target
from advoi.ingestion.models import IngestItem, PriorityBand

_DEV_KEYWORDS = (
    "implement",
    "build",
    "fix",
    "bug",
    "feature",
    "refactor",
    "deploy",
    "ship",
    "code",
    "develop",
    "api",
    "endpoint",
)
_URGENT_KEYWORDS = ("urgent", "p0", "critical", "blocker", "asap", "production down")

_SLUG_ALIASES: dict[str, str] = {
    "advoi-system": "advoi",
    "firstmate-fleet": "clapart",
    "hermes-beacon": "hermes",
    "gem-dev-shop": "gem-dev-shop",
    "clapart": "clapart",
    "advoi": "advoi",
    "hermes": "hermes",
}


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9][a-z0-9_-]{2,}", text.lower()))


def _score_venture(venture_id: str, name: str, tags: tuple[str, ...], haystack: str) -> float:
    score = 0.0
    vid = venture_id.lower().replace("_", "-")
    if vid in haystack:
        score += 3.0
    for part in vid.split("-"):
        if len(part) > 2 and part in haystack:
            score += 1.0
    if name.lower() in haystack:
        score += 2.0
    for tag in tags:
        if tag.lower() in haystack:
            score += 1.5
    return score


def _priority_band(text: str) -> tuple[PriorityBand, int]:
    lowered = text.lower()
    if any(k in lowered for k in _URGENT_KEYWORDS):
        return "high", 85
    if any(k in lowered for k in _DEV_KEYWORDS):
        return "medium", 60
    return "low", 35


def _dev_recommended(text: str) -> bool:
    lowered = text.lower()
    return any(k in lowered for k in _DEV_KEYWORDS)


def _summarize(text: str, *, limit: int = 240) -> str:
    line = " ".join(text.split())
    if len(line) <= limit:
        return line
    return line[: limit - 3] + "..."


def _fleet_slug_for_venture(venture_id: str | None, explicit_slug: str | None) -> str:
    if explicit_slug:
        return _SLUG_ALIASES.get(explicit_slug.lower(), explicit_slug.lower())
    if venture_id and venture_id in _SLUG_ALIASES:
        mapped = _SLUG_ALIASES[venture_id]
        if mapped:
            return mapped
    target = resolve_execution_target()
    if target.get("fleet_slug"):
        return str(target["fleet_slug"])
    return resolve_active_project()


def route_document(
    text: str,
    filename: str,
    *,
    project_hint: str | None = None,
    venture_hint: str | None = None,
) -> dict[str, Any]:
    haystack = f"{filename}\n{text}".lower()
    tokens = _tokens(haystack)

    if project_hint:
        slug = _SLUG_ALIASES.get(project_hint.lower(), project_hint.lower())
        venture_id = None
        for v in VENTURES:
            if v.id == venture_hint or v.id.replace("-", "") in slug.replace("-", ""):
                venture_id = v.id
                break
        priority, score = _priority_band(haystack)
        return {
            "venture_id": venture_id,
            "project_slug": slug,
            "route_confidence": 1.0,
            "priority": priority,
            "priority_score": score,
            "dev_recommended": _dev_recommended(haystack),
            "summary": _summarize(text),
            "task_hint": _task_hint(text, filename),
        }

    best_venture: str | None = None
    best_score = 0.0
    for venture in VENTURES:
        s = _score_venture(venture.id, venture.name, venture.tags, haystack)
        for token in tokens:
            if token in venture.id.lower() or token in "-".join(venture.tags):
                s += 0.5
        if s > best_score:
            best_score = s
            best_venture = venture.id

    active_target = resolve_execution_target()
    active_slug = active_target.get("fleet_slug") or resolve_active_project()
    slug_scores: dict[str, float] = {active_slug: 1.0}
    for alias, slug in _SLUG_ALIASES.items():
        if alias in haystack or slug in tokens:
            slug_scores[slug] = slug_scores.get(slug, 0) + 2.5

    project_slug = max(slug_scores, key=slug_scores.get) if slug_scores else active_slug
    if best_venture:
        mapped = _fleet_slug_for_venture(best_venture, None)
        if best_score >= slug_scores.get(project_slug, 0):
            project_slug = mapped

    confidence = min(1.0, max(best_score, slug_scores.get(project_slug, 0)) / 5.0)
    priority, priority_score = _priority_band(haystack)

    return {
        "venture_id": best_venture,
        "project_slug": project_slug,
        "route_confidence": round(confidence, 2),
        "priority": priority,
        "priority_score": priority_score,
        "dev_recommended": _dev_recommended(haystack),
        "summary": _summarize(text),
        "task_hint": _task_hint(text, filename),
    }


def _task_hint(text: str, filename: str) -> str:
    summary = _summarize(text, limit=180)
    return f"Process ingested file {filename}: {summary}"


def apply_route(item: IngestItem, route: dict[str, Any], *, text: str) -> IngestItem:
    item.venture_id = route.get("venture_id")
    item.project_slug = route.get("project_slug")
    item.route_confidence = float(route.get("route_confidence") or 0)
    item.priority = route.get("priority", "medium")
    item.priority_score = int(route.get("priority_score") or 50)
    item.dev_recommended = bool(route.get("dev_recommended"))
    item.summary = str(route.get("summary") or "")
    item.task_hint = str(route.get("task_hint") or "")
    item.content_preview = _summarize(text, limit=400)
    item.status = "routed"
    return item