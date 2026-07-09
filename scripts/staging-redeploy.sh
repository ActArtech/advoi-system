#!/usr/bin/env bash
# Redeploy ADVoi staging with 6 specialist agent daemons + Phase 4 routes.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ADVOI_ENV_FILE:-deploy/.env}"
COMPOSE_FILES="-f docker-compose.yml -f deploy/docker-compose.staging.yml"
if grep -qE '^LETTA_ENABLED=(true|1|yes)' "$ENV_FILE" 2>/dev/null; then
  COMPOSE_FILES="${COMPOSE_FILES} -f deploy/docker-compose.letta.yml"
  echo "==> Letta overlay enabled (letta-network)"
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE — copy deploy/.env.staging.example first" >&2
  exit 1
fi

echo "==> Pull latest (optional)"
git pull --ff-only 2>/dev/null || true

echo "==> Build images"
docker compose --env-file "$ENV_FILE" $COMPOSE_FILES --profile app build advoi-api advoi-web advoi-voice

echo "==> Up stack (6 agent daemons + API + web + voice)"
docker compose --env-file "$ENV_FILE" $COMPOSE_FILES --profile app up -d \
  advoi-api advoi-web advoi-voice \
  advoi-agent-fleet advoi-agent-briefs advoi-agent-review \
  advoi-agent-systems advoi-agent-memory advoi-agent-guardian \
  redis postgres advoi-memory-bridge livekit

echo "==> Wait for API health"
for i in $(seq 1 30); do
  if docker compose --env-file "$ENV_FILE" $COMPOSE_FILES exec -T advoi-api \
    python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" 2>/dev/null; then
    break
  fi
  sleep 2
done

API_HOST="${STOREFRONT_HOST:-advoi.keyteller.com}"
curl -sf "https://${API_HOST}/api/health" || echo "WARN: health check failed"
curl -sf -X POST "https://${API_HOST}/api/agents/run-six?refresh=true" -H "Content-Type: application/json" -d '{}' || true
curl -sf "https://${API_HOST}/api/diagnostics/guardian" || echo "WARN: guardian diagnostics missing"

echo "Done. Expect agents_total=6 at https://${API_HOST}/api/health"