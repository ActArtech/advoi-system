#!/usr/bin/env bash
# Verify ADVoi memory stack — Hindsight, optional Letta, Postgres, Redis.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-${ROOT}/deploy/.env}"
HERMES_CONTAINER="${HERMES_CONTAINER:-hermes}"

if [[ -f "${ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
fi

echo "==> ADVoi memory health"

echo "--- Hermes memory provider ---"
if docker ps --format '{{.Names}}' | grep -qx "${HERMES_CONTAINER}"; then
  docker exec "${HERMES_CONTAINER}" hermes memory status || true
else
  echo "WARN: ${HERMES_CONTAINER} not running"
fi

echo "--- Hindsight bridge probe ---"
if docker ps --format '{{.Names}}' | grep -qx "${HERMES_CONTAINER}"; then
  docker exec "${HERMES_CONTAINER}" python /vps-projects/advoi/scripts/hindsight-bridge.py \
    --json '{"action":"recall","query":"ADVoi portfolio","limit":3}' 2>/dev/null | head -c 400 || \
    echo "WARN: hindsight bridge not ready (daemon may still be warming)"
fi

echo "--- Letta (optional) ---"
if [[ "${LETTA_ENABLED:-false}" == "true" && -n "${LETTA_BASE_URL:-}" ]]; then
  curl -sf "${LETTA_BASE_URL}/v1/health" && echo " OK" || echo "WARN: Letta unreachable at ${LETTA_BASE_URL}"
else
  echo "SKIP: LETTA_ENABLED=false"
fi

echo "--- Postgres / Redis ---"
if [[ -f "${ROOT}/docker-compose.yml" && -f "${ENV_FILE}" ]]; then
  docker compose -f "${ROOT}/docker-compose.yml" --env-file "${ENV_FILE}" ps postgres redis 2>/dev/null || true
fi

echo "==> memory-health complete"