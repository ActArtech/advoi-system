#!/usr/bin/env bash
# Deploy ADVoi STAGING (current branch) -> advoi-staging.keyteller.com
# Usage:
#   bash /var/www/advoi/deploy-staging.sh
#   bash /var/www/advoi/deploy-staging.sh feature/my-branch
set -euo pipefail

WWW="/var/www/advoi"
STAGING="$WWW/staging"
ENV_FILE="$WWW/.env.staging"
BRANCH="${1:-}"
COMPOSE_PROJECT="${COMPOSE_PROJECT_NAME:-advoi-staging}"

cd "$STAGING"

if [[ -n "$BRANCH" ]]; then
  git fetch origin "$BRANCH"
  git checkout "$BRANCH"
  git pull --ff-only origin "$BRANCH" 2>/dev/null || true
else
  echo "Current branch: $(git branch --show-current)"
  git pull --ff-only origin "$(git branch --show-current)" 2>/dev/null || true
fi

cp "$ENV_FILE" deploy/.env
chmod 600 deploy/.env

export DEPLOY_MODE=staging
export ENV_FILE=deploy/.env
export COMPOSE_PROJECT_NAME="$COMPOSE_PROJECT"

# shellcheck disable=SC1090
set -a
source deploy/.env
set +a

export ADVOI_ENV="$STAGING/deploy/.env"
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

echo "==> STAGING deployed @ $(git rev-parse --short HEAD) ($(git branch --show-current))"
docker compose -p "$COMPOSE_PROJECT" --env-file deploy/.env ps

HOST="${STOREFRONT_HOST:-advoi-staging.keyteller.com}"
if curl -sf "https://${HOST}/api/health" >/dev/null; then
  curl -sf "https://${HOST}/api/health" && echo ""
else
  curl -k -sI "https://${HOST}" | head -1 || true
  echo "WARN: health check failed (DNS A record for ${HOST}? Traefik cert?)"
fi