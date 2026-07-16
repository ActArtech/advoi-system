#!/usr/bin/env bash
# Deploy ADVoi LIVE (main branch) -> advoi.keyteller.com
# Usage: bash /var/www/advoi/deploy-live.sh
set -euo pipefail

WWW="/var/www/advoi"
LIVE="$WWW/live"
ENV_FILE="$WWW/.env.live"
COMPOSE_PROJECT="${COMPOSE_PROJECT_NAME:-advoi-live}"

cd "$LIVE"
git fetch origin master main 2>/dev/null || git fetch origin
git checkout master 2>/dev/null || git checkout main
git pull --ff-only origin "$(git branch --show-current)"

cp "$ENV_FILE" deploy/.env
chmod 600 deploy/.env

export DEPLOY_MODE=staging
export ENV_FILE=deploy/.env
export COMPOSE_PROJECT_NAME="$COMPOSE_PROJECT"

# shellcheck disable=SC1090
set -a
source deploy/.env
set +a

export ADVOI_ENV="$LIVE/deploy/.env"
if [[ -x scripts/ensure-deploy-secrets.sh ]]; then
  bash scripts/ensure-deploy-secrets.sh
fi

docker compose -p "$COMPOSE_PROJECT" \
  -f docker-compose.yml \
  -f deploy/docker-compose.staging.yml \
  -f deploy/docker-compose.www.yml \
  --env-file deploy/.env \
  --profile app \
  up -d --build --remove-orphans

echo "==> LIVE deployed @ $(git rev-parse --short HEAD)"
docker compose -p "$COMPOSE_PROJECT" --env-file deploy/.env ps

HOST="${STOREFRONT_HOST:-advoi.keyteller.com}"
if curl -sf "https://${HOST}/api/health" >/dev/null; then
  curl -sf "https://${HOST}/api/health" && echo ""
else
  curl -k -sI "https://${HOST}" | head -1 || true
  echo "WARN: health check failed (stop /opt/advoi if it still owns ${HOST})"
fi