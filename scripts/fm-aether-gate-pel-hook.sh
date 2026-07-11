#!/usr/bin/env bash
# PEL hook for fm-aether-gate — source after gate run for advoi ventures.
# Usage (from fm-aether-gate.sh tail, when writable):
#   source /data/projects/advoi/scripts/fm-aether-gate-pel-hook.sh
#   emit_gate_snapshot_pel "$?" "${REPORT:-${FM_AETHER_GATE_REPORT:-/data/aether-gate-latest.md}}"
set -euo pipefail

emit_gate_snapshot_pel() {
  local exit_code="${1:-2}"
  local report_path="${2:-${FM_AETHER_GATE_REPORT:-/data/aether-gate-latest.md}}"
  local slug="${FM_ACTIVE_PROJECT:-}"
  local lab="${FM_AETHER_PROJECT_ROOT:-}"

  if [[ "$exit_code" != "0" && "$exit_code" != "1" ]]; then
    return 0
  fi

  if [[ "$slug" != "advoi" && "$lab" != *"advoi"* ]]; then
    return 0
  fi

  if [[ -z "${DATABASE_URL:-}" ]]; then
    echo "PEL_GATE_SNAPSHOT_SKIP: DATABASE_URL unset"
    return 0
  fi

  local hook_dir
  hook_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  local repo_root
  repo_root="$(cd "${hook_dir}/.." && pwd)"
  local emit_py="${repo_root}/scripts/emit-gate-snapshot-pel.py"

  if [[ ! -f "$emit_py" ]]; then
    echo "PEL_GATE_SNAPSHOT_SKIP: missing ${emit_py}"
    return 0
  fi

  if command -v uv >/dev/null 2>&1; then
    (cd "$repo_root" && uv run python "$emit_py" "$report_path" "$exit_code") || true
  else
    PYTHONPATH="${repo_root}${PYTHONPATH:+:$PYTHONPATH}" python3 "$emit_py" "$report_path" "$exit_code" || true
  fi
}