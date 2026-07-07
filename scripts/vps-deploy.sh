#!/usr/bin/env bash
# Deploy ADVoi stack at /opt/advoi — isolated compose project, no sibling overwrites.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

ENV_FILE="${ENV_FILE:-deploy/.env}"
COMPOSE_BASE=(docker compose -f docker-compose.yml)
COMPOSE_FILES=(-f docker-compose.yml)

if [[ -f deploy/docker-compose.staging.yml ]] && [[ "${DEPLOY_MODE:-}" == "staging" ]]; then
  COMPOSE_FILES+=(-f deploy/docker-compose.staging.yml)
fi

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing ${ENV_FILE}. Copy deploy/.env.staging.example first."
  exit 1
fi

# Shelve — canonical secrets (team ktteam / staging → deploy/.env)
if [[ -f /opt/shelve/scripts/shelve-pull-deploy.sh ]]; then
  # shellcheck source=/dev/null
  source /opt/shelve/scripts/shelve-pull-deploy.sh
  shelve_pull_deploy "${ROOT}"
  # Shelve copy can corrupt long OPENAI keys — re-overlay from clapart when available.
fi

if [[ -x "${ROOT}/scripts/ensure-deploy-secrets.sh" ]]; then
  bash "${ROOT}/scripts/ensure-deploy-secrets.sh"
fi

# shellcheck disable=SC1090
set -a
source "${ENV_FILE}"
set +a

PROFILE_ARGS=()
if [[ "${1:-}" == "--profile" ]] && [[ -n "${2:-}" ]]; then
  PROFILE_ARGS=(--profile "${2}")
  shift 2
fi

echo "==> ADVoi compose project: advoi (slug isolated)"
docker compose "${COMPOSE_FILES[@]}" --env-file "${ENV_FILE}" "${PROFILE_ARGS[@]}" up -d --build "$@"

docker compose "${COMPOSE_FILES[@]}" --env-file "${ENV_FILE}" ps