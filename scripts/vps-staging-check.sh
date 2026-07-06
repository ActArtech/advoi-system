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
  echo "--- HTTPS probe (Traefik) — expect HTTP/2 200 ---"
  STATUS=$(curl -k -sI "https://${HOST}" | head -1)
  echo "${STATUS}"
  if echo "${STATUS}" | grep -qE ' 200 | 301 | 302 '; then
    echo "OK: route reachable"
  else
    echo "WARN: not 200 yet — check DNS (grey cloud), Traefik labels (${SLUG}-web), app profile"
    exit 1
  fi
fi

echo "--- Port registry reminder ---"
echo "Register in /opt/shared/port-registry.md:"
echo "  slug=${SLUG} | staging=${HOST} | path=/opt/advoi"