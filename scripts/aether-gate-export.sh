#!/usr/bin/env bash
# ADVoi Aether — export aether-gate-latest.md snapshot to repo path and/or PEL.
#
# Closes the moat gap: gate file was VPS-only on the fleet tree with no
# GitHub audit trail or portfolio_events row. This entrypoint is safe for
# nightly cron or post-gate (after fm-aether-gate / aether-publish-atomic).
#
# Exports:
#   1. Git-auditable path: data/aether/aether-gate-latest.md (default)
#   2. PEL portfolio_events row: source=aether type=governance_decision
#
# Usage:
#   bash scripts/aether-gate-export.sh
#   bash scripts/aether-gate-export.sh --no-pel
#   bash scripts/aether-gate-export.sh --no-repo
#   FM_AETHER_GATE_EXPORT_GIT_COMMIT=1 bash scripts/aether-gate-export.sh
#
# Typical sequence after a proactive / gate cycle:
#   FM_ACTIVE_PROJECT=advoi bash /opt/firstmate/scripts/fm-aether-gate.sh
#   bash scripts/aether-publish-atomic.sh
#   bash scripts/aether-gate-export.sh
#
# Cron example (fleet host, nightly after gate):
#   30 2 * * * FM_ACTIVE_PROJECT=advoi \
#     FIRSTMATE_FLEET_PATH=/opt/firstmate-fleet \
#     bash /data/projects/advoi/scripts/aether-gate-export.sh \
#     >> /var/log/advoi-aether-gate-export.log 2>&1
#
# Env:
#   FIRSTMATE_FLEET_PATH              Fleet tree with aether-gate-latest.md
#   FM_AETHER_PROJECT_ROOT            Advoi repo root (default: this checkout)
#   FM_AETHER_GATE_REPORT             Override gate source path
#   FM_AETHER_GATE_EXPORT_DEST        Override in-repo dest path
#   FM_AETHER_GATE_EXPORT_NO_REPO=1   Skip repo file write
#   FM_AETHER_GATE_EXPORT_NO_PEL=1    Skip PEL append
#   FM_AETHER_GATE_EXPORT_GIT_COMMIT=1  git add+commit dest when changed (no push)
#   ADVOI_PEL_MEMORY=true             In-memory PEL (tests / no Postgres)
#   DATABASE_URL                      Postgres for real PEL rows
#
# Test hooks:
#   FM_AETHER_GATE_EXPORT_SOURCE      Explicit source (tmp gate in tests)
#   FM_AETHER_GATE_EXPORT_DEST        Explicit dest under tmpdir
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJ="${FM_AETHER_PROJECT_ROOT:-${ROOT}}"
export FM_AETHER_PROJECT_ROOT="${PROJ}"

SOURCE_ARGS=()
if [[ -n "${FM_AETHER_GATE_EXPORT_SOURCE:-}" ]]; then
  SOURCE_ARGS+=(--source "${FM_AETHER_GATE_EXPORT_SOURCE}")
elif [[ -n "${FM_AETHER_GATE_REPORT:-}" ]]; then
  SOURCE_ARGS+=(--source "${FM_AETHER_GATE_REPORT}")
fi

DEST_ARGS=()
if [[ -n "${FM_AETHER_GATE_EXPORT_DEST:-}" ]]; then
  DEST_ARGS+=(--dest "${FM_AETHER_GATE_EXPORT_DEST}")
fi

EXTRA_ARGS=("$@")

log() { echo "$@"; }

log "==> aether-gate-export"
log "    project: ${PROJ}"
log "    fleet:   ${FIRSTMATE_FLEET_PATH:-/opt/firstmate-fleet}"

# Prefer uv when available so the package import path matches T0 tests.
if command -v uv >/dev/null 2>&1 && [[ -f "${ROOT}/pyproject.toml" ]]; then
  cd "${ROOT}"
  uv run python -m advoi.aether.gate_export \
    --repo "${PROJ}" \
    "${SOURCE_ARGS[@]+"${SOURCE_ARGS[@]}"}" \
    "${DEST_ARGS[@]+"${DEST_ARGS[@]}"}" \
    "${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}"
else
  PYTHONPATH="${ROOT}${PYTHONPATH:+:${PYTHONPATH}}" \
    python3 -m advoi.aether.gate_export \
      --repo "${PROJ}" \
      "${SOURCE_ARGS[@]+"${SOURCE_ARGS[@]}"}" \
      "${DEST_ARGS[@]+"${DEST_ARGS[@]}"}" \
      "${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}"
fi

log "==> aether-gate-export done"
