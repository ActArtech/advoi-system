"""Atomic publish of Aether gate + proactive + directives to the fleet tree.

Writes three artifacts all-or-nothing into ``FIRSTMATE_FLEET_PATH`` (or an
explicit destination):

- ``aether-gate-latest.md`` — gate verdict (read by ``advoi.aether.gate``)
- ``aether-proactive-latest.json`` — proactive feed
- ``AETHER-DIRECTIVES.md`` — human-readable directives companion

Algorithm (same filesystem as dest):

1. Stage all three files under ``.aether-publish-staging-<token>/``
2. Snapshot any existing finals into ``.aether-publish-backup-<token>/``
3. ``os.replace`` each staged file into the destination (atomic per file)
4. On mid-commit failure, restore from backup so prior artifacts stay intact
5. Always remove staging/backup dirs

Used by ``scripts/aether-publish-atomic.sh`` and T0 tests.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any

# Canonical names on the fleet tree (must match gate.py / feed consumers).
GATE_ARTIFACT = "aether-gate-latest.md"
PROACTIVE_ARTIFACT = "aether-proactive-latest.json"
DIRECTIVES_ARTIFACT = "AETHER-DIRECTIVES.md"

ARTIFACT_NAMES: tuple[str, str, str] = (
    GATE_ARTIFACT,
    PROACTIVE_ARTIFACT,
    DIRECTIVES_ARTIFACT,
)


class PublishError(RuntimeError):
    """Raised when atomic publish cannot complete; prior artifacts left intact."""


def default_fleet_root() -> Path:
    return Path(os.getenv("FIRSTMATE_FLEET_PATH", "/opt/firstmate-fleet"))


def build_artifact_map(
    *,
    gate_text: str,
    proactive_text: str,
    directives_text: str,
) -> dict[str, str]:
    """Build the three-file map; empty strings are rejected."""
    mapping = {
        GATE_ARTIFACT: gate_text,
        PROACTIVE_ARTIFACT: proactive_text,
        DIRECTIVES_ARTIFACT: directives_text,
    }
    for name, body in mapping.items():
        if not isinstance(body, str) or not body.strip():
            raise PublishError(f"artifact empty or missing content: {name}")
    return mapping


def read_sources(
    *,
    gate_path: Path,
    proactive_path: Path,
    directives_path: Path,
) -> dict[str, str]:
    """Load the three source files from disk."""
    missing = [
        str(p)
        for p in (gate_path, proactive_path, directives_path)
        if not p.is_file()
    ]
    if missing:
        raise PublishError(f"source artifact(s) missing: {', '.join(missing)}")
    return build_artifact_map(
        gate_text=gate_path.read_text(encoding="utf-8"),
        proactive_text=proactive_path.read_text(encoding="utf-8"),
        directives_text=directives_path.read_text(encoding="utf-8"),
    )


def publish_atomic(
    dest_dir: Path | str,
    artifacts: Mapping[str, str],
    *,
    _fail_after_stage: bool = False,
    _fail_mid_commit_after: int | None = None,
) -> dict[str, Any]:
    """Write *artifacts* into *dest_dir* all-or-nothing.

    Args:
        dest_dir: Fleet tree (or test tmp) directory.
        artifacts: Map of basename → text content. Must include all of
            :data:`ARTIFACT_NAMES` (extra keys allowed).
        _fail_after_stage: Test hook — raise after staging, before commit.
        _fail_mid_commit_after: Test hook — raise after N successful replaces.

    Returns:
        Result dict with ``dest``, ``artifacts`` (list of names), ``token``.

    Raises:
        PublishError: on validation or I/O failure. Prior dest files are
        restored when a commit was partially applied.
    """
    dest = Path(dest_dir)
    required = set(ARTIFACT_NAMES)
    names = list(ARTIFACT_NAMES)
    extras = [k for k in artifacts if k not in required]
    # Always publish the three required names first, in stable order.
    ordered = names + extras
    for name in ARTIFACT_NAMES:
        if name not in artifacts:
            raise PublishError(f"missing required artifact key: {name}")
        body = artifacts[name]
        if not isinstance(body, str) or not body.strip():
            raise PublishError(f"artifact empty or missing content: {name}")

    dest.mkdir(parents=True, exist_ok=True)
    token = uuid.uuid4().hex
    staging = dest / f".aether-publish-staging-{token}"
    backup = dest / f".aether-publish-backup-{token}"
    committed: list[str] = []

    try:
        staging.mkdir(exist_ok=False)
        for name in ordered:
            body = artifacts[name]
            if not isinstance(body, str) or not body.strip():
                raise PublishError(f"artifact empty or missing content: {name}")
            (staging / name).write_text(body, encoding="utf-8")

        if _fail_after_stage:
            raise PublishError("injected failure after stage (test hook)")

        # Snapshot existing finals so mid-commit failure can roll back.
        existing = [n for n in ordered if (dest / n).is_file()]
        if existing:
            backup.mkdir(exist_ok=False)
            for name in existing:
                shutil.copy2(dest / name, backup / name)

        try:
            for i, name in enumerate(ordered):
                if _fail_mid_commit_after is not None and i >= _fail_mid_commit_after:
                    raise PublishError(
                        f"injected mid-commit failure after {i} replace(s) (test hook)"
                    )
                os.replace(staging / name, dest / name)
                committed.append(name)
        except Exception:
            # Restore prior content for any file we already replaced.
            for name in committed:
                bak = backup / name
                if bak.is_file():
                    os.replace(bak, dest / name)
            raise

        return {
            "dest": str(dest),
            "artifacts": list(ordered),
            "token": token,
            "committed": list(committed),
        }
    except PublishError:
        raise
    except OSError as exc:
        raise PublishError(f"atomic publish I/O failed: {exc}") from exc
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        shutil.rmtree(backup, ignore_errors=True)


def publish_from_paths(
    *,
    dest_dir: Path | str,
    gate_path: Path | str,
    proactive_path: Path | str,
    directives_path: Path | str,
) -> dict[str, Any]:
    """Load three sources from disk and publish atomically into *dest_dir*."""
    artifacts = read_sources(
        gate_path=Path(gate_path),
        proactive_path=Path(proactive_path),
        directives_path=Path(directives_path),
    )
    return publish_atomic(dest_dir, artifacts)


def _cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Atomically publish Aether gate verdict, proactive feed, and "
            "directives to the fleet tree (all-or-nothing)."
        )
    )
    parser.add_argument(
        "--fleet",
        default=os.getenv("FIRSTMATE_FLEET_PATH", "/opt/firstmate-fleet"),
        help="Destination fleet tree (default: FIRSTMATE_FLEET_PATH)",
    )
    parser.add_argument("--gate", required=True, help="Path to aether-gate-latest.md source")
    parser.add_argument(
        "--proactive",
        required=True,
        help="Path to aether-proactive-latest.json source",
    )
    parser.add_argument(
        "--directives",
        required=True,
        help="Path to AETHER-DIRECTIVES.md source",
    )
    args = parser.parse_args(argv)

    try:
        result = publish_from_paths(
            dest_dir=args.fleet,
            gate_path=args.gate,
            proactive_path=args.proactive,
            directives_path=args.directives,
        )
    except PublishError as exc:
        print(f"aether-publish: FAIL — {exc}", file=sys.stderr)
        return 1

    print(
        "aether-publish: OK — "
        f"wrote {', '.join(result['artifacts'])} → {result['dest']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
