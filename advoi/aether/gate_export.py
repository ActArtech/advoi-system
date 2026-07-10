"""Export Aether gate snapshot into the advoi repo path and/or PEL.

Closes the moat gap that ``aether-gate-latest.md`` lived only on the fleet
tree (VPS-only, no GitHub / portfolio_events audit trail).

Typical use (post-gate or nightly cron)::

    bash scripts/aether-gate-export.sh

Pure API for T0 tests: :func:`export_gate_snapshot`.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from advoi.aether.gate import parse_gate_markdown
from advoi.aether.models import GateSnapshot

# Canonical basename on fleet tree and in-repo export path.
GATE_ARTIFACT = "aether-gate-latest.md"
# Git-auditable default under the advoi repo (committed when ops elects).
DEFAULT_REPO_RELATIVE = f"data/aether/{GATE_ARTIFACT}"

# PEL payload marker so analytics can filter gate exports.
PEL_EXPORT_KIND = "gate_snapshot"


class GateExportError(RuntimeError):
    """Raised when the gate source is missing or export cannot complete."""


def default_fleet_root() -> Path:
    return Path(os.getenv("FIRSTMATE_FLEET_PATH", "/opt/firstmate-fleet"))


def default_repo_root() -> Path:
    """Repo root: FM_AETHER_PROJECT_ROOT, else parent of advoi package."""
    env = os.getenv("FM_AETHER_PROJECT_ROOT")
    if env:
        return Path(env)
    # advoi/aether/gate_export.py → parents[2] = repo root
    return Path(__file__).resolve().parents[2]


def resolve_source_gate(
    *,
    fleet_root: Path | None = None,
    source_path: Path | str | None = None,
    repo_root: Path | None = None,
) -> Path:
    """Resolve the gate markdown source (fleet first, then repo data/).

    Order:
    1. Explicit *source_path* / ``FM_AETHER_GATE_REPORT``
    2. ``{fleet}/aether-gate-latest.md``
    3. ``/data/aether-gate-latest.md`` (host shared path)
    4. ``{repo}/data/aether-gate-latest.md``
    5. ``{repo}/data/aether/aether-gate-latest.md`` (prior export)
    """
    if source_path is not None:
        return Path(source_path)
    env_src = os.getenv("FM_AETHER_GATE_REPORT")
    if env_src:
        return Path(env_src)

    root = fleet_root or default_fleet_root()
    candidates = [
        root / GATE_ARTIFACT,
        Path("/data") / GATE_ARTIFACT,
    ]
    repo = repo_root or default_repo_root()
    candidates.extend(
        [
            repo / "data" / GATE_ARTIFACT,
            repo / "data" / "aether" / GATE_ARTIFACT,
        ]
    )
    for path in candidates:
        if path.is_file():
            return path
    # Prefer fleet path in error messages (canonical runtime location).
    return root / GATE_ARTIFACT


def content_sha256(text: str) -> str:
    """Stable content hash for audit payloads (full SHA-256 hex)."""
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def read_gate_text(source: Path) -> str:
    """Read gate markdown; raise :class:`GateExportError` if missing/empty."""
    if not source.is_file():
        raise GateExportError(f"gate source missing: {source}")
    try:
        text = source.read_text(encoding="utf-8")
    except OSError as exc:
        raise GateExportError(f"gate source unreadable: {source}: {exc}") from exc
    if not text.strip():
        raise GateExportError(f"gate source empty: {source}")
    return text


def snapshot_from_text(text: str, *, path: str | None = None) -> GateSnapshot:
    """Parse gate markdown into a :class:`GateSnapshot`."""
    snap = parse_gate_markdown(text)
    if path is not None:
        snap.path = path
    return snap


def _guardian_for_verdict(verdict: str) -> str:
    """Map gate verdict → PEL guardian_status vocabulary."""
    mapping = {
        "pass": "allowed",
        "hold": "pending",
        "fail": "denied",
        "unknown": "not_required",
    }
    return mapping.get(verdict, "not_required")


def write_gate_to_repo(
    text: str,
    *,
    dest_path: Path,
) -> dict[str, Any]:
    """Write gate markdown to the repo-relative export path (atomic replace).

    Creates parent dirs. Uses a same-dir temp file + ``os.replace``.
    """
    dest = Path(dest_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(f".{dest.name}.tmp-{os.getpid()}")
    try:
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, dest)
    except OSError as exc:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise GateExportError(f"failed to write repo export: {dest}: {exc}") from exc

    return {
        "dest": str(dest),
        "bytes": len(text.encode("utf-8")),
        "sha256": content_sha256(text),
    }


def maybe_git_commit(
    *,
    repo_root: Path,
    relative_path: str,
    message: str,
    enabled: bool,
) -> dict[str, Any] | None:
    """Optionally ``git add`` + ``git commit`` the export file when changed.

    No-op when *enabled* is False, git is unavailable, or there is no diff.
    Never pushes. Safe for cron on a disposable worktree or ops host.
    """
    if not enabled:
        return None
    root = Path(repo_root)
    rel = relative_path.replace("\\", "/")
    try:
        add = subprocess.run(
            ["git", "-C", str(root), "add", "--", rel],
            capture_output=True,
            text=True,
            check=False,
        )
        if add.returncode != 0:
            return {
                "committed": False,
                "reason": "git_add_failed",
                "stderr": (add.stderr or "").strip()[:400],
            }
        # Exit 1 means no staged changes for this path (or clean).
        diff = subprocess.run(
            ["git", "-C", str(root), "diff", "--cached", "--quiet", "--", rel],
            capture_output=True,
            text=True,
            check=False,
        )
        if diff.returncode == 0:
            return {"committed": False, "reason": "no_change"}
        commit = subprocess.run(
            ["git", "-C", str(root), "commit", "-m", message, "--", rel],
            capture_output=True,
            text=True,
            check=False,
        )
        if commit.returncode != 0:
            return {
                "committed": False,
                "reason": "git_commit_failed",
                "stderr": (commit.stderr or "").strip()[:400],
            }
        return {"committed": True, "reason": "ok", "message": message}
    except FileNotFoundError:
        return {"committed": False, "reason": "git_not_found"}
    except OSError as exc:
        return {"committed": False, "reason": "git_os_error", "error": str(exc)}


def pel_payload_from_export(
    *,
    snap: GateSnapshot,
    text: str,
    source_path: str,
    repo_path: str | None,
    sha256: str,
) -> dict[str, Any]:
    """Build a compact PEL payload (preview only — no full dump required)."""
    return {
        "kind": PEL_EXPORT_KIND,
        "artifact": GATE_ARTIFACT,
        "verdict": snap.verdict,
        "active_slug": snap.active_slug,
        "content_sha256": sha256,
        "source_path": source_path,
        "repo_path": repo_path,
        "raw_preview": (text or "")[:400],
        "found": snap.found,
    }


async def emit_gate_export_pel(
    *,
    snap: GateSnapshot,
    text: str,
    source_path: str,
    repo_path: str | None,
    sha256: str,
    venture_id: str | None = None,
) -> str | None:
    """Append a portfolio_events row for this gate export (best-effort)."""
    from advoi.analytics.pel import (
        EventSource,
        EventType,
        GuardianStatus,
        safe_append_event,
    )

    venture = (venture_id or snap.active_slug or "advoi").strip() or "advoi"
    payload = pel_payload_from_export(
        snap=snap,
        text=text,
        source_path=source_path,
        repo_path=repo_path,
        sha256=sha256,
    )
    return await safe_append_event(
        venture_id=venture,
        source=EventSource.AETHER,
        event_type=EventType.GOVERNANCE_DECISION,
        payload=payload,
        guardian_status=GuardianStatus(_guardian_for_verdict(snap.verdict)),
        execution_ref=f"gate-export:{sha256[:16]}",
    )


async def export_gate_snapshot(
    *,
    fleet_root: Path | None = None,
    source_path: Path | str | None = None,
    repo_root: Path | None = None,
    dest_path: Path | str | None = None,
    write_repo: bool = True,
    emit_pel: bool = True,
    git_commit: bool = False,
    venture_id: str | None = None,
    commit_message: str | None = None,
) -> dict[str, Any]:
    """Export gate snapshot to repo path and/or PEL.

    Args:
        fleet_root: FIRSTMATE_FLEET_PATH override.
        source_path: Explicit gate markdown path.
        repo_root: Advoi project root for default dest + optional git commit.
        dest_path: Explicit repo export path (default ``data/aether/…``).
        write_repo: When True, write the markdown into the advoi tree.
        emit_pel: When True, append a ``governance_decision`` PEL row.
        git_commit: When True, commit the dest file if it changed (no push).
        venture_id: PEL venture_id override (default active_slug / advoi).
        commit_message: Optional git commit message.

    Returns:
        Result dict with source, dest, sha256, verdict, pel_event_id, git.
    """
    if not write_repo and not emit_pel:
        raise GateExportError("export requires at least one of write_repo or emit_pel")

    repo = Path(repo_root) if repo_root is not None else default_repo_root()
    source = resolve_source_gate(
        fleet_root=fleet_root,
        source_path=source_path,
        repo_root=repo,
    )
    text = read_gate_text(source)
    snap = snapshot_from_text(text, path=str(source))
    sha = content_sha256(text)

    dest: Path | None = None
    repo_write: dict[str, Any] | None = None
    if write_repo:
        if dest_path is not None:
            dest = Path(dest_path)
        else:
            dest = repo / DEFAULT_REPO_RELATIVE
        repo_write = write_gate_to_repo(text, dest_path=dest)

    pel_id: str | None = None
    if emit_pel:
        pel_id = await emit_gate_export_pel(
            snap=snap,
            text=text,
            source_path=str(source),
            repo_path=str(dest) if dest is not None else None,
            sha256=sha,
            venture_id=venture_id,
        )

    git_result: dict[str, Any] | None = None
    if write_repo and dest is not None:
        try:
            rel = str(dest.relative_to(repo))
        except ValueError:
            rel = str(dest)
        msg = commit_message or (
            f"chore(aether): export gate snapshot ({snap.verdict}"
            f"{f', {snap.active_slug}' if snap.active_slug else ''})"
        )
        git_result = maybe_git_commit(
            repo_root=repo,
            relative_path=rel,
            message=msg,
            enabled=git_commit,
        )

    return {
        "ok": True,
        "source": str(source),
        "dest": str(dest) if dest is not None else None,
        "sha256": sha,
        "verdict": snap.verdict,
        "active_slug": snap.active_slug,
        "write_repo": write_repo,
        "emit_pel": emit_pel,
        "repo_write": repo_write,
        "pel_event_id": pel_id,
        "git": git_result,
    }


def export_gate_snapshot_sync(**kwargs: Any) -> dict[str, Any]:
    """Sync wrapper around :func:`export_gate_snapshot` for shell / CLI."""
    return asyncio.run(export_gate_snapshot(**kwargs))


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Export aether-gate-latest.md into the advoi repo path and/or "
            "a portfolio_events (PEL) governance_decision row."
        )
    )
    parser.add_argument(
        "--source",
        default=None,
        help="Gate markdown source (default: fleet / FM_AETHER_GATE_REPORT)",
    )
    parser.add_argument(
        "--dest",
        default=None,
        help=f"Repo export path (default: {{repo}}/{DEFAULT_REPO_RELATIVE})",
    )
    parser.add_argument(
        "--repo",
        default=None,
        help="Advoi project root (default: FM_AETHER_PROJECT_ROOT or detect)",
    )
    parser.add_argument(
        "--fleet",
        default=None,
        help="Fleet tree for source resolution (default: FIRSTMATE_FLEET_PATH)",
    )
    parser.add_argument(
        "--no-repo",
        action="store_true",
        help="Skip writing the in-repo markdown snapshot",
    )
    parser.add_argument(
        "--no-pel",
        action="store_true",
        help="Skip PEL portfolio_events append",
    )
    parser.add_argument(
        "--git-commit",
        action="store_true",
        help="git add+commit the dest file when it changed (never push)",
    )
    parser.add_argument(
        "--venture-id",
        default=None,
        help="PEL venture_id (default: gate active_slug or advoi)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print full result JSON on stdout",
    )
    args = parser.parse_args(argv)

    write_repo = not args.no_repo
    emit_pel = not args.no_pel
    # Env overrides (cron-friendly)
    if os.getenv("FM_AETHER_GATE_EXPORT_NO_REPO", "").strip() in {"1", "true", "yes"}:
        write_repo = False
    if os.getenv("FM_AETHER_GATE_EXPORT_NO_PEL", "").strip() in {"1", "true", "yes"}:
        emit_pel = False
    git_commit = args.git_commit or _env_bool("FM_AETHER_GATE_EXPORT_GIT_COMMIT", False)

    try:
        result = export_gate_snapshot_sync(
            fleet_root=Path(args.fleet) if args.fleet else None,
            source_path=args.source,
            repo_root=Path(args.repo) if args.repo else None,
            dest_path=args.dest,
            write_repo=write_repo,
            emit_pel=emit_pel,
            git_commit=git_commit,
            venture_id=args.venture_id,
        )
    except GateExportError as exc:
        print(f"aether-gate-export: FAIL — {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        dest = result.get("dest") or "(repo write skipped)"
        pel = result.get("pel_event_id") or "(none)"
        print(
            "aether-gate-export: OK — "
            f"verdict={result.get('verdict')} "
            f"sha256={str(result.get('sha256', ''))[:12]}… "
            f"dest={dest} pel={pel}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
