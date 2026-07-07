#!/usr/bin/env bash
# Canonical secrets on VPS — clapart LLM keys win over Shelve corruption.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT}/deploy/.env"

# Shelve / hand-edits sometimes omit trailing newlines — repair merged KEY=valueKEY=value lines.
if [[ -f "${ENV_FILE}" ]]; then
  python3 - "${ENV_FILE}" <<'PY'
import re, sys
path = sys.argv[1]
text = open(path, encoding="utf-8", errors="replace").read()
text = re.sub(
    r"(?<=[^\n])(?=[A-Z][A-Z0-9_]+=)",
    "\n",
    text,
)
if text and not text.endswith("\n"):
    text += "\n"
open(path, "w", encoding="utf-8").write(text)
PY
fi

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

# Hindsight HTTP bridge — app containers reach Hermes via this service (docker.sock isolated here)
if grep -q '^HINDSIGHT_BRIDGE_URL=' "${ENV_FILE}"; then
  sed -i 's|^HINDSIGHT_BRIDGE_URL=.*|HINDSIGHT_BRIDGE_URL=http://advoi-memory-bridge:8095|' "${ENV_FILE}"
else
  echo "HINDSIGHT_BRIDGE_URL=http://advoi-memory-bridge:8095" >> "${ENV_FILE}"
fi

# Agent daemon tick interval (background cache refresh — voice taps are immediate)
if grep -q '^ADVOI_AGENT_INTERVAL_SECS=' "${ENV_FILE}"; then
  sed -i 's|^ADVOI_AGENT_INTERVAL_SECS=.*|ADVOI_AGENT_INTERVAL_SECS=45|' "${ENV_FILE}"
else
  echo "ADVOI_AGENT_INTERVAL_SECS=45" >> "${ENV_FILE}"
fi

echo "OK: deploy secrets validated"