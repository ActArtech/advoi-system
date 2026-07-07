#!/usr/bin/env bash
# Canonical secrets on VPS — clapart LLM keys win over Shelve corruption.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT}/deploy/.env"

if [[ -x "${ROOT}/scripts/sync-llm-keys-from-clapart.sh" ]] && [[ -f /opt/clapart/deploy/.env ]]; then
  bash "${ROOT}/scripts/sync-llm-keys-from-clapart.sh"
elif [[ -f /opt/clapart/deploy/.env ]]; then
  bash "${ROOT}/scripts/sync-llm-keys-from-clapart.sh"
fi

_validate() {
  local key="$1"
  local val
  val="$(grep -m1 "^${key}=" "${ENV_FILE}" | cut -d= -f2- || true)"
  if [[ -z "${val}" ]]; then
    echo "ERROR: missing ${key} in ${ENV_FILE}" >&2
    return 1
  fi
  if [[ "${val}" == *true ]] || [[ ${#val} -gt 200 ]]; then
    echo "ERROR: ${key} looks corrupted (len=${#val})" >&2
    return 1
  fi
}

_validate OPENAI_API_KEY || exit 1

# Fleet paths — must exist on VPS host
if [[ -f /opt/firstmate-fleet/scripts/fm-hermes-trigger.sh ]]; then
  if grep -q '^FIRSTMATE_TRIGGER_SCRIPT=' "${ENV_FILE}"; then
    sed -i 's|^FIRSTMATE_TRIGGER_SCRIPT=.*|FIRSTMATE_TRIGGER_SCRIPT=/opt/firstmate-fleet/scripts/fm-hermes-trigger.sh|' "${ENV_FILE}"
  else
    echo "FIRSTMATE_TRIGGER_SCRIPT=/opt/firstmate-fleet/scripts/fm-hermes-trigger.sh" >> "${ENV_FILE}"
  fi
  if grep -q '^FIRSTMATE_FLEET_PATH=' "${ENV_FILE}"; then
    sed -i 's|^FIRSTMATE_FLEET_PATH=.*|FIRSTMATE_FLEET_PATH=/opt/firstmate-fleet|' "${ENV_FILE}"
  else
    echo "FIRSTMATE_FLEET_PATH=/opt/firstmate-fleet" >> "${ENV_FILE}"
  fi
fi

echo "OK: deploy secrets validated"