#!/usr/bin/env bash
# Run fm-aether-gate and emit gate_snapshot PEL rows on PASS for advoi.
#
# Use when /opt/firstmate/scripts/fm-aether-gate.sh cannot be patched in-place:
#   FM_ACTIVE_PROJECT=advoi FM_AETHER_PROJECT_ROOT=/data/projects/advoi \
#     bash scripts/aether-gate-with-pel.sh
set -euo pipefail

GATE_SCRIPT="${FM_AETHER_GATE_SCRIPT:-/opt/firstmate/scripts/fm-aether-gate.sh}"
HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
REPORT="${FM_AETHER_GATE_REPORT:-/data/aether-gate-latest.md}"

if [[ ! -f "$GATE_SCRIPT" ]]; then
  echo "ERROR: gate script not found: $GATE_SCRIPT" >&2
  exit 2
fi

EXIT_CODE=0
bash "$GATE_SCRIPT" "$@" || EXIT_CODE=$?

# shellcheck source=fm-aether-gate-pel-hook.sh
source "${HOOK_DIR}/fm-aether-gate-pel-hook.sh"
emit_gate_snapshot_pel "$EXIT_CODE" "$REPORT"

exit "$EXIT_CODE"