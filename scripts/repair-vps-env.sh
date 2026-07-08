#!/usr/bin/env bash
# One-shot VPS env repair + Traefik label refresh. Run on VPS as deploy user.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

export ADVOI_SHELVE_PULL=false
export DEPLOY_MODE=staging

bash scripts/ensure-deploy-secrets.sh

if ! grep -q '^PROJECT_SLUG=advoi' deploy/.env; then
  echo "ERROR: PROJECT_SLUG still missing after repair" >&2
  exit 1
fi
if ! grep -q '^STOREFRONT_HOST=advoi.keyteller.com' deploy/.env; then
  echo "ERROR: STOREFRONT_HOST still missing after repair" >&2
  exit 1
fi

echo "==> Recreating edge + agent services (Traefik labels need valid PROJECT_SLUG + STOREFRONT_HOST)"
docker compose -f docker-compose.yml -f deploy/docker-compose.staging.yml \
  --env-file deploy/.env --profile app up -d --force-recreate \
  advoi-api advoi-web advoi-voice \
  advoi-agent-fleet advoi-agent-briefs advoi-agent-review

echo "==> Labels (api):"
docker inspect advoi-advoi-api-1 --format '{{index .Config.Labels "traefik.http.routers.advoi-api.rule"}}' 2>/dev/null || true

echo "OK: env repaired and edge services recreated"