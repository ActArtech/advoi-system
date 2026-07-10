#!/usr/bin/env bash
# Forward voice/text intent to existing firstmate-fleet — never modifies fleet files.
# Message is a single hermes verb/phrase (e.g. arm, stop, work <task>).
set -euo pipefail

_resolve_fleet_trigger() {
  if [[ -n "${FIRSTMATE_TRIGGER_SCRIPT:-}" ]]; then
    printf '%s\n' "${FIRSTMATE_TRIGGER_SCRIPT}"
    return 0
  fi
  local candidate
  for candidate in \
    /opt/firstmate-fleet/scripts/fm-hermes-trigger.sh \
    /opt/firstmate/scripts/fm-hermes-trigger.sh
  do
    if [[ -f "${candidate}" ]]; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done
  # Default documented layout (may be missing until fleet is installed).
  printf '%s\n' "/opt/firstmate-fleet/scripts/fm-hermes-trigger.sh"
}

FLEET_TRIGGER="$(_resolve_fleet_trigger)"
MSG="${*:-fleet status}"

if [[ ! -x "${FLEET_TRIGGER}" ]] && [[ ! -f "${FLEET_TRIGGER}" ]]; then
  echo "ERROR: Fleet trigger not found: ${FLEET_TRIGGER}"
  echo "ADVoi reads fleet at /opt/firstmate-fleet — clone fleet separately if missing."
  echo "Or set FIRSTMATE_TRIGGER_SCRIPT to fm-hermes-trigger.sh."
  exit 1
fi

exec bash "${FLEET_TRIGGER}" "${MSG}"