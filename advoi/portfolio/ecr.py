"""Execution Context Registry (ECR) — canonical active venture / fleet slug routing."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

import yaml

ExecutionSource = Literal["ecr", "gate", "fallback"]

_DEFAULT_EXECUTION_CONTEXT_PATH = "data/portfolio/execution-context.yaml"

_CONTEXT: dict[str, Any] | None = None
_SESSION_OVERRIDE: dict[str, Any] | None = None


def execution_context_path() -> Path:
    """Resolve ECR path from EXECUTION_CONTEXT_PATH env (evaluated at call time)."""
    return Path(os.getenv("EXECUTION_CONTEXT_PATH", _DEFAULT_EXECUTION_CONTEXT_PATH))


def _builtin_execution_context() -> dict[str, Any]:
    """Fallback when execution-context.yaml is missing or invalid."""
    return {
        "version": 1,
        "active_execution_target": {
            "venture_id": "firstmate-fleet",
            "fleet_slug": "clapart",
            "github_repo": "ActArtech/clapart",
            "develop_path": "develop",
            "staging_url": None,
        },
        "ventures": [
            {
                "venture_id": "advoi-system",
                "fleet_slug": "advoi",
                "repo_path": "/opt/advoi",
                "github_repo": "ActArtech/advoi-system",
                "tags": ["advoi-system", "advoi"],
            },
            {
                "venture_id": "firstmate-fleet",
                "fleet_slug": "clapart",
                "repo_path": "/opt/firstmate-fleet",
                "github_repo": "ActArtech/firstmate-fleet",
                "tags": ["firstmate-fleet"],
            },
            {
                "venture_id": "clapart",
                "fleet_slug": "clapart",
                "repo_path": "/opt/clapart",
                "github_repo": "ActArtech/clapart",
                "tags": ["clapart"],
            },
            {
                "venture_id": "gem-dev-shop",
                "fleet_slug": "gem-dev-shop",
                "repo_path": "/opt/gem-dev-shop",
                "github_repo": "ActArtech/gem-dev-shop",
                "tags": ["gem-dev-shop", "aether-active"],
            },
            {
                "venture_id": "hermes-beacon",
                "fleet_slug": "hermes",
                "repo_path": "/opt/hermes",
                "github_repo": "ActArtech/hermes-beacon",
                "tags": ["hermes-beacon", "hermes"],
            },
        ],
    }


def load_execution_context(*, path: Path | None = None) -> dict[str, Any]:
    """Load ECR YAML from disk (cached). Returns builtin fallback when missing."""
    global _CONTEXT  # noqa: PLW0603
    cfg_path = path or execution_context_path()
    if _CONTEXT is not None and path is None:
        return _CONTEXT
    if not cfg_path.is_file():
        ctx = _builtin_execution_context()
        ctx["_from_file"] = False
    else:
        try:
            raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict) or not raw.get("active_execution_target"):
                ctx = _builtin_execution_context()
                ctx["_from_file"] = False
            else:
                ctx = raw
                ctx["_from_file"] = True
        except (OSError, yaml.YAMLError, TypeError, ValueError):
            ctx = _builtin_execution_context()
            ctx["_from_file"] = False
    if path is None:
        _CONTEXT = ctx
    return ctx


def reload_execution_context(*, path: Path | None = None) -> dict[str, Any]:
    """Clear cache and reload ECR (tests and hot config)."""
    global _CONTEXT  # noqa: PLW0603
    _CONTEXT = None
    return load_execution_context(path=path)


def set_session_active_venture(venture_id: str | None) -> dict[str, Any]:
    """PWA/voice session override for active venture. None clears override."""
    global _SESSION_OVERRIDE  # noqa: PLW0603
    if not venture_id:
        _SESSION_OVERRIDE = None
        return resolve_execution_target()

    matched = _match_venture(load_execution_context(), venture_id)
    if matched:
        _SESSION_OVERRIDE = {
            "venture_id": str(matched.get("venture_id") or venture_id),
            "fleet_slug": str(matched.get("fleet_slug") or venture_id),
            "github_repo": matched.get("github_repo"),
        }
    else:
        _SESSION_OVERRIDE = {
            "venture_id": venture_id.strip(),
            "fleet_slug": venture_id.strip().lower(),
            "github_repo": None,
        }
    return resolve_execution_target()


def clear_session_active_venture() -> None:
    set_session_active_venture(None)


def _venture_entries(ctx: dict[str, Any]) -> list[dict[str, Any]]:
    ventures = ctx.get("ventures") or []
    if isinstance(ventures, dict):
        return [
            {"venture_id": vid, **(entry if isinstance(entry, dict) else {})}
            for vid, entry in ventures.items()
        ]
    return [v for v in ventures if isinstance(v, dict)]


def _match_venture(ctx: dict[str, Any], slug: str) -> dict[str, Any] | None:
    needle = slug.strip().lower()
    if not needle:
        return None
    for entry in _venture_entries(ctx):
        venture_id = str(entry.get("venture_id", "")).lower()
        fleet_slug = str(entry.get("fleet_slug", "")).lower()
        tags = [str(t).lower() for t in entry.get("tags", [])]
        if needle in {venture_id, fleet_slug} or needle in tags:
            return entry
        if needle in venture_id:
            return entry
        if any(needle in tag for tag in tags):
            return entry
    return None


def _target_dict(
    *,
    venture_id: str | None,
    fleet_slug: str | None,
    github_repo: str | None,
    source: ExecutionSource,
    develop_path: str | None = None,
    staging_url: str | None = None,
    config_path: str | None = None,
) -> dict[str, Any]:
    return {
        "venture_id": venture_id,
        "fleet_slug": fleet_slug,
        "github_repo": github_repo,
        "develop_path": develop_path,
        "staging_url": staging_url,
        "source": source,
        "config_path": config_path or str(execution_context_path()),
    }


def resolve_execution_target(*, gate_active_slug: str | None = None) -> dict[str, Any]:
    """Resolve active execution target from ECR, optional gate slug, or env fallback."""
    if _SESSION_OVERRIDE:
        return _target_dict(
            venture_id=str(_SESSION_OVERRIDE.get("venture_id") or ""),
            fleet_slug=str(_SESSION_OVERRIDE.get("fleet_slug") or ""),
            github_repo=_SESSION_OVERRIDE.get("github_repo"),
            source="session",
        )

    ctx = load_execution_context()
    active = ctx.get("active_execution_target") or {}

    gate_slug = (gate_active_slug or "").strip()
    if gate_slug:
        matched = _match_venture(ctx, gate_slug)
        if matched:
            return _target_dict(
                venture_id=str(matched.get("venture_id") or ""),
                fleet_slug=str(matched.get("fleet_slug") or gate_slug),
                github_repo=matched.get("github_repo") or active.get("github_repo"),
                develop_path=active.get("develop_path"),
                staging_url=active.get("staging_url"),
                source="gate",
            )

    if not ctx.get("_from_file"):
        env_slug = (os.getenv("FM_HERMES_PROJECT") or "").strip().lower()
        if env_slug:
            matched = _match_venture(ctx, env_slug)
            return _target_dict(
                venture_id=(matched or {}).get("venture_id"),
                fleet_slug=env_slug,
                github_repo=(matched or {}).get("github_repo") or active.get("github_repo"),
                develop_path=active.get("develop_path"),
                staging_url=active.get("staging_url"),
                source="fallback",
            )

    fleet_slug = str(active.get("fleet_slug") or "").strip()
    if fleet_slug:
        source: ExecutionSource = "ecr" if ctx.get("_from_file") else "fallback"
        return _target_dict(
            venture_id=active.get("venture_id"),
            fleet_slug=fleet_slug,
            github_repo=active.get("github_repo"),
            develop_path=active.get("develop_path"),
            staging_url=active.get("staging_url"),
            source=source,
        )

    env_slug = (os.getenv("FM_HERMES_PROJECT") or "").strip().lower()
    fallback_slug = env_slug or "clapart"
    matched = _match_venture(ctx, fallback_slug)
    return _target_dict(
        venture_id=(matched or {}).get("venture_id") or "firstmate-fleet",
        fleet_slug=fallback_slug,
        github_repo=(matched or {}).get("github_repo") or "ActArtech/clapart",
        develop_path=active.get("develop_path") or "develop",
        staging_url=active.get("staging_url"),
        source="fallback",
    )