#!/usr/bin/env bash
# One-time bootstrap /var/www/advoi (Clapart-style staging + live checkouts).
# Run on VPS as deploy@187.77.140.216
set -euo pipefail

WWW="/var/www/advoi"
REMOTE="${ADVOI_REMOTE:-git@github-advoi:ActArtech/advoi-system.git}"
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

echo "==> ADVoi www bootstrap -> ${WWW}"

sudo mkdir -p "$WWW"
sudo chown deploy:deploy "$WWW"

if [[ ! -d "${WWW}/staging/.git" ]]; then
  git clone --branch master "$REMOTE" "${WWW}/staging"
  cd "${WWW}/staging"
  git checkout -B staging master
else
  echo "  keep: ${WWW}/staging"
fi

if [[ ! -d "${WWW}/live/.git" ]]; then
  git clone --branch master "$REMOTE" "${WWW}/live"
else
  echo "  keep: ${WWW}/live"
fi

for script in deploy-staging.sh deploy-live.sh promote-to-staging.sh promote-to-live.sh checkout-pr.sh; do
  cp "${REPO_ROOT}/scripts/www/${script}" "${WWW}/${script}"
  chmod +x "${WWW}/${script}"
done

if [[ ! -f "${WWW}/.env.staging" ]]; then
  if [[ -f /opt/advoi/deploy/.env ]]; then
    cp /opt/advoi/deploy/.env "${WWW}/.env.staging"
    sed -i \
      -e 's/^COMPOSE_PROJECT_NAME=.*/COMPOSE_PROJECT_NAME=advoi-staging/' \
      -e 's/^PROJECT_SLUG=.*/PROJECT_SLUG=advoi-staging/' \
      -e 's/^STOREFRONT_HOST=.*/STOREFRONT_HOST=advoi-staging.keyteller.com/' \
      -e 's/^POSTGRES_PORT=.*/POSTGRES_PORT=5439/' \
      -e 's/^POSTGRES_DB=.*/POSTGRES_DB=advoi_staging/' \
      -e 's|^DATABASE_URL=.*|DATABASE_URL=postgresql://advoi:advoi@postgres:5432/advoi_staging|' \
      -e 's/^REDIS_PORT=.*/REDIS_PORT=6383/' \
      -e 's/^ADVOI_API_HOST_PORT=.*/ADVOI_API_HOST_PORT=8012/' \
      -e 's/^ADVOI_API_PORT=.*/ADVOI_API_PORT=8012/' \
      -e 's/^ADVOI_VOICE_PORT=.*/ADVOI_VOICE_PORT=8013/' \
      -e 's|^NEXT_PUBLIC_LIVEKIT_TOKEN_ENDPOINT=.*|NEXT_PUBLIC_LIVEKIT_TOKEN_ENDPOINT=https://advoi-staging.keyteller.com/api/livekit/token|' \
      -e 's|^NEXT_PUBLIC_ADVOI_API_URL=.*|NEXT_PUBLIC_ADVOI_API_URL=https://advoi-staging.keyteller.com/api|' \
      -e 's/^LIVEKIT_HOST=.*/LIVEKIT_HOST=livekit.advoi-staging.keyteller.com/' \
      -e 's|^LIVEKIT_URL=.*|LIVEKIT_URL=wss://livekit.advoi-staging.keyteller.com|' \
      -e 's/^LIVEKIT_HOST_PORT=.*/LIVEKIT_HOST_PORT=7882/' \
      -e 's/^LIVEKIT_RTC_TCP_PORT=.*/LIVEKIT_RTC_TCP_PORT=7883/' \
      -e 's/^LIVEKIT_RTC_UDP_RANGE=.*/LIVEKIT_RTC_UDP_RANGE=51100-51200/' \
      -e 's/^ADVOI_MEMORY_BRIDGE_PORT=.*/ADVOI_MEMORY_BRIDGE_PORT=8096/' \
      -e 's/^HINDSIGHT_BANK_ID=.*/HINDSIGHT_BANK_ID=advoi-staging-portfolio/' \
      -e 's|^ADVOI_ALLOWED_ORIGINS=.*|ADVOI_ALLOWED_ORIGINS=https://advoi-staging.keyteller.com|' \
      -e 's/^OTEL_SERVICE_NAME=.*/OTEL_SERVICE_NAME=advoi-staging/' \
      "${WWW}/.env.staging" 2>/dev/null || true
    echo "  wrote: ${WWW}/.env.staging (from /opt/advoi/deploy/.env)"
  elif [[ -f "${REPO_ROOT}/deploy/.env.www.staging.example" ]]; then
    cp "${REPO_ROOT}/deploy/.env.www.staging.example" "${WWW}/.env.staging"
    echo "  wrote: ${WWW}/.env.staging (from example — add secrets)"
  fi
  chmod 600 "${WWW}/.env.staging"
fi

if [[ ! -f "${WWW}/.env.live" ]]; then
  if [[ -f "${REPO_ROOT}/deploy/.env.www.live.example" ]]; then
    cp "${REPO_ROOT}/deploy/.env.www.live.example" "${WWW}/.env.live"
  elif [[ -f /opt/advoi/deploy/.env ]]; then
    cp /opt/advoi/deploy/.env "${WWW}/.env.live"
  fi
  chmod 600 "${WWW}/.env.live"
  echo "  wrote: ${WWW}/.env.live"
fi

# Ensure www overlay exists in checkouts (may lag until git pull)
for tier in staging live; do
  if [[ -f "${REPO_ROOT}/deploy/docker-compose.www.yml" ]]; then
    cp "${REPO_ROOT}/deploy/docker-compose.www.yml" "${WWW}/${tier}/deploy/docker-compose.www.yml"
  fi
done

echo ""
echo "Done. Next:"
echo "  1. DNS: advoi-staging.keyteller.com + livekit.advoi-staging.keyteller.com -> VPS IP"
echo "  2. bash ${WWW}/deploy-staging.sh"
echo "  3. Register fleet: cd /opt/firstmate-fleet && bash scripts/register-project.sh advoi ActArtech/advoi-system no-mistakes"