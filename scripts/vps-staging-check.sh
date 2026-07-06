#!/usr/bin/env bash
# Smoke check ADVoi staging — read-only against VPS routes.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

ENV_FILE="${ENV_FILE:-deploy/.env}"
# shellcheck disable=SC1090
[[ -f "${ENV_FILE}" ]] && source "${ENV_FILE}"

HOST="${STOREFRONT_HOST:-advoi.keyteller.com}"
SLUG="${PROJECT_SLUG:-advoi}"

echo "==> ADVoi staging check (${SLUG})"
echo "Host: https://${HOST}"

if docker compose -f docker-compose.yml --env-file "${ENV_FILE}" ps 2>/dev/null | grep -q advoi; then
  docker compose -f docker-compose.yml --env-file "${ENV_FILE}" ps
else
  echo "WARN: advoi compose stack not running"
fi

if command -v curl >/dev/null 2>&1; then
  echo "--- HTTPS probe (Traefik) ---"
  curl -k -sI "https://${HOST}" | head -5 || echo "No route yet (deploy staging overlay + DNS)"
fi

echo "--- Port registry reminder ---"
echo "Register in /opt/shared/port-registry.md:"
echo "  slug=${SLUG} | staging=${HOST} | path=/opt/advoi"