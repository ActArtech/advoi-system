#!/usr/bin/env bash
# ADVoi Aether — atomic publish of gate + proactive + directives to fleet tree.
#
# Publishes three artifacts into FIRSTMATE_FLEET_PATH (all-or-nothing):
#   aether-gate-latest.md
#   aether-proactive-latest.json
#   AETHER-DIRECTIVES.md
#
# Implementation: temp staging dir + backup + os.replace (see
# advoi.aether.publish_atomic). On any failure before/during commit, prior
# fleet artifacts are left intact (or restored).
#
# Usage:
#   bash scripts/aether-publish-atomic.sh
#   FIRSTMATE_FLEET_PATH=/opt/firstmate-fleet bash scripts/aether-publish-atomic.sh
#
# Typical sequence after a proactive cycle:
#   FM_ACTIVE_PROJECT=advoi bash /opt/firstmate/scripts/fm-aether-gate.sh
#   bash scripts/aether-publish-atomic.sh
#   FM_AETHER_GATE_REQUIRED=1 bash scripts/aether-feed-cron.sh
#
# Env:
#   FIRSTMATE_FLEET_PATH   Destination fleet tree (default /opt/firstmate-fleet)
#   FM_AETHER_PROJECT_ROOT Project root with docs/aether/ (default: this repo)
#   FM_AETHER_GATE_REPORT  Source gate markdown (default: prefer /data then
#                          $ROOT/data/aether-gate-latest.md)
#   FM_AETHER_PROACTIVE    Override proactive JSON path
#   FM_AETHER_DIRECTIVES   Override directives markdown path
#
# Test hooks:
#   FM_AETHER_PUBLISH_DEST  Override fleet (tmp fleet tree in tests)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJ="${FM_AETHER_PROJECT_ROOT:-${ROOT}}"
FLEET="${FM_AETHER_PUBLISH_DEST:-${FIRSTMATE_FLEET_PATH:-/opt/firstmate-fleet}}"

# Gate report: same resolution preference as fm-aether-gate.sh
if [[ -n "${FM_AETHER_GATE_REPORT:-}" ]]; then
  GATE_SRC="${FM_AETHER_GATE_REPORT}"
elif [[ -f "/data/aether-gate-latest.md" ]]; then
  GATE_SRC="/data/aether-gate-latest.md"
elif [[ -f "${ROOT}/data/aether-gate-latest.md" ]]; then
  GATE_SRC="${ROOT}/data/aether-gate-latest.md"
else
  GATE_SRC="${ROOT}/data/aether-gate-latest.md"
fi

PROACTIVE_SRC="${FM_AETHER_PROACTIVE:-${PROJ}/docs/aether/aether-proactive-latest.json}"
DIRECTIVES_SRC="${FM_AETHER_DIRECTIVES:-${PROJ}/docs/aether/AETHER-DIRECTIVES.md}"

log() { echo "$@"; }

log "==> aether-publish-atomic"
log "    fleet:      ${FLEET}"
log "    gate:       ${GATE_SRC}"
log "    proactive:  ${PROACTIVE_SRC}"
log "    directives: ${DIRECTIVES_SRC}"

for src in "${GATE_SRC}" "${PROACTIVE_SRC}" "${DIRECTIVES_SRC}"; do
  if [[ ! -f "${src}" ]]; then
    log "ERROR: source missing: ${src}" >&2
    exit 1
  fi
done

mkdir -p "${FLEET}"

# Prefer uv when available so the package import path matches T0 tests.
if command -v uv >/dev/null 2>&1 && [[ -f "${ROOT}/pyproject.toml" ]]; then
  cd "${ROOT}"
  uv run python -m advoi.aether.publish_atomic \
    --fleet "${FLEET}" \
    --gate "${GATE_SRC}" \
    --proactive "${PROACTIVE_SRC}" \
    --directives "${DIRECTIVES_SRC}"
else
  PYTHONPATH="${ROOT}${PYTHONPATH:+:${PYTHONPATH}}" \
    python3 -m advoi.aether.publish_atomic \
      --fleet "${FLEET}" \
      --gate "${GATE_SRC}" \
      --proactive "${PROACTIVE_SRC}" \
      --directives "${DIRECTIVES_SRC}"
fi

log "==> aether-publish-atomic done"
