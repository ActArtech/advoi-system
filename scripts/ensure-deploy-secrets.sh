#!/usr/bin/env bash
# Canonical secrets on VPS — clapart LLM keys win over Shelve corruption.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT}/deploy/.env"
STAGING_EXAMPLE="${ROOT}/deploy/.env.staging.example"

_env_char_split() {
  local f="$1"
  [[ ! -f "${f}" ]] && return 1
  local n=0
  n="$(grep -cE '^.$' "${f}" 2>/dev/null)" || n=0
  [[ "${n}" =~ ^[0-9]+$ ]] || n=0
  [[ "${n}" -gt 20 ]]
}

# Shelve char-split corruption — restore canonical template before any sed/python edits.
if _env_char_split "${ENV_FILE}"; then
  echo "WARN: ${ENV_FILE} is char-split corrupt — restoring from .env.staging.example"
  cp "${STAGING_EXAMPLE}" "${ENV_FILE}"
  sed -i 's/change-me-advoi-pg/advoi/' "${ENV_FILE}" 2>/dev/null || true
fi

# Shelve / hand-edits sometimes omit trailing newlines — repair merged KEY=valueKEY=value lines.
if [[ -f "${ENV_FILE}" ]] && ! _env_char_split "${ENV_FILE}"; then
  python3 - "${ENV_FILE}" <<'PY'
import re, sys
path = sys.argv[1]
text = open(path, encoding="utf-8", errors="replace").read()
# Only split merged lines (value immediately followed by KEY=), not inside KEY names like PROJECT_SLUG.
text = re.sub(
    r"(?<=[a-z0-9.])(?=[A-Z][A-Z0-9_]+=)",
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

# Staging VPS must not run on the local dev template (missing Traefik hosts).
_ensure_staging_hosts() {
  if [[ "${DEPLOY_MODE:-}" != "staging" ]]; then
    return 0
  fi
  local missing=0
  for key in STOREFRONT_HOST LIVEKIT_HOST LIVEKIT_URL; do
    if ! grep -q "^${key}=" "${ENV_FILE}" 2>/dev/null; then
      missing=1
      break
    fi
  done
  if [[ "${missing}" -eq 1 ]] || ! grep -q '^STOREFRONT_HOST=advoi.keyteller.com' "${ENV_FILE}" 2>/dev/null; then
    echo "WARN: staging deploy/.env missing Traefik hosts — merging from .env.staging.example"
    cp "${STAGING_EXAMPLE}" "${ENV_FILE}.staging-merge"
    sed -i 's/change-me-advoi-pg/advoi/' "${ENV_FILE}.staging-merge" 2>/dev/null || true
    # Preserve live secrets from the current file when re-merging.
    for key in OPENAI_API_KEY OPENROUTER_API_KEY LIVEKIT_API_KEY LIVEKIT_API_SECRET POSTGRES_PASSWORD; do
      val="$(grep -m1 "^${key}=" "${ENV_FILE}" 2>/dev/null | cut -d= -f2- || true)"
      if [[ -n "${val}" ]] && [[ "${val}" != change-me* ]]; then
        if grep -q "^${key}=" "${ENV_FILE}.staging-merge"; then
          sed -i "s|^${key}=.*|${key}=${val}|" "${ENV_FILE}.staging-merge"
        else
          echo "${key}=${val}" >> "${ENV_FILE}.staging-merge"
        fi
      fi
    done
    mv "${ENV_FILE}.staging-merge" "${ENV_FILE}"
  fi
  # Canonical staging identity for Traefik labels.
  if grep -q '^PROJECT_SLUG=' "${ENV_FILE}"; then
    sed -i 's|^PROJECT_SLUG=.*|PROJECT_SLUG=advoi|' "${ENV_FILE}"
  else
    echo "PROJECT_SLUG=advoi" >> "${ENV_FILE}"
  fi
  if grep -q '^STOREFRONT_HOST=' "${ENV_FILE}"; then
    sed -i 's|^STOREFRONT_HOST=.*|STOREFRONT_HOST=advoi.keyteller.com|' "${ENV_FILE}"
  else
    echo "STOREFRONT_HOST=advoi.keyteller.com" >> "${ENV_FILE}"
  fi
  if grep -q '^ADVOI_ENV=' "${ENV_FILE}"; then
    sed -i 's|^ADVOI_ENV=.*|ADVOI_ENV=staging|' "${ENV_FILE}"
  else
    echo "ADVOI_ENV=staging" >> "${ENV_FILE}"
  fi
  if grep -q '^ADVOI_ALLOWED_ORIGINS=' "${ENV_FILE}"; then
    sed -i 's|^ADVOI_ALLOWED_ORIGINS=.*|ADVOI_ALLOWED_ORIGINS=https://advoi.keyteller.com|' "${ENV_FILE}"
  else
    echo "ADVOI_ALLOWED_ORIGINS=https://advoi.keyteller.com" >> "${ENV_FILE}"
  fi
  if grep -q '^NEXT_PUBLIC_LIVEKIT_TOKEN_ENDPOINT=' "${ENV_FILE}"; then
    sed -i 's|^NEXT_PUBLIC_LIVEKIT_TOKEN_ENDPOINT=.*|NEXT_PUBLIC_LIVEKIT_TOKEN_ENDPOINT=https://advoi.keyteller.com/api/livekit/token|' "${ENV_FILE}"
  else
    echo "NEXT_PUBLIC_LIVEKIT_TOKEN_ENDPOINT=https://advoi.keyteller.com/api/livekit/token" >> "${ENV_FILE}"
  fi
  if grep -q '^NEXT_PUBLIC_ADVOI_API_URL=' "${ENV_FILE}"; then
    sed -i 's|^NEXT_PUBLIC_ADVOI_API_URL=.*|NEXT_PUBLIC_ADVOI_API_URL=https://advoi.keyteller.com/api|' "${ENV_FILE}"
  else
    echo "NEXT_PUBLIC_ADVOI_API_URL=https://advoi.keyteller.com/api" >> "${ENV_FILE}"
  fi
}

_ensure_staging_hosts

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
_agent_interval="${ADVOI_AGENT_INTERVAL_SECS:-}"
if [[ -z "${_agent_interval}" ]]; then
  if [[ "${DEPLOY_MODE:-}" == "staging" ]]; then
    _agent_interval="15"
  else
    _agent_interval="45"
  fi
fi
if grep -q '^ADVOI_AGENT_INTERVAL_SECS=' "${ENV_FILE}"; then
  sed -i "s|^ADVOI_AGENT_INTERVAL_SECS=.*|ADVOI_AGENT_INTERVAL_SECS=${_agent_interval}|" "${ENV_FILE}"
else
  echo "ADVOI_AGENT_INTERVAL_SECS=${_agent_interval}" >> "${ENV_FILE}"
fi

echo "OK: deploy secrets validated"