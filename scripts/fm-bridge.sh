#!/usr/bin/env bash
# Forward voice/text intent to existing firstmate-fleet — never modifies fleet files.
set -euo pipefail

FLEET_TRIGGER="${FIRSTMATE_TRIGGER_SCRIPT:-/opt/firstmate-fleet/scripts/fm-hermes-trigger.sh}"
MSG="${*:-fleet status}"

if [[ ! -x "${FLEET_TRIGGER}" ]] && [[ ! -f "${FLEET_TRIGGER}" ]]; then
  echo "ERROR: Fleet trigger not found: ${FLEET_TRIGGER}"
  echo "ADVoi reads fleet at /opt/firstmate-fleet — clone fleet separately if missing."
  exit 1
fi

exec bash "${FLEET_TRIGGER}" "${MSG}"