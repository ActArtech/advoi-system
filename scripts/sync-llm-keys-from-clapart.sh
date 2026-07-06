#!/usr/bin/env bash
# Copy LLM keys from clapart deploy/.env into advoi deploy/.env (clone-safe).
# Prefers OPENROUTER_API_KEY (clapart voicecomp pattern); falls back to OPENAI_API_KEY.
set -euo pipefail

CLAPART_ENV="${CLAPART_ENV:-/opt/clapart/deploy/.env}"
ADVOI_ENV="${ADVOI_ENV:-/opt/advoi/deploy/.env}"

if [[ ! -f "${CLAPART_ENV}" ]]; then
  echo "ERROR: missing ${CLAPART_ENV}" >&2
  exit 1
fi
if [[ ! -f "${ADVOI_ENV}" ]]; then
  echo "ERROR: missing ${ADVOI_ENV}" >&2
  exit 1
fi

_read_key() {
  local file="$1" name="$2"
  grep -m1 "^${name}=" "${file}" 2>/dev/null | cut -d= -f2- || true
}

set_kv() {
  local key="$1" value="$2"
  if grep -q "^${key}=" "${ADVOI_ENV}"; then
    sed -i "s|^${key}=.*|${key}=${value}|" "${ADVOI_ENV}"
  else
    echo "${key}=${value}" >> "${ADVOI_ENV}"
  fi
}

router_key="$(_read_key "${CLAPART_ENV}" OPENROUTER_API_KEY)"
openai_key="$(_read_key "${CLAPART_ENV}" OPENAI_API_KEY)"

if [[ -n "${router_key}" ]]; then
  set_kv OPENROUTER_API_KEY "${router_key}"
  echo "OK: copied OPENROUTER_API_KEY from ${CLAPART_ENV}"
elif [[ -n "${openai_key}" ]]; then
  set_kv OPENAI_API_KEY "${openai_key}"
  echo "OK: copied OPENAI_API_KEY from ${CLAPART_ENV} (no OPENROUTER key found)"
else
  echo "WARN: no OPENROUTER_API_KEY or OPENAI_API_KEY in ${CLAPART_ENV}" >&2
  exit 1
fi