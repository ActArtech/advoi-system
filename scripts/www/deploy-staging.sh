#!/usr/bin/env bash
# Deploy ADVoi STAGING -> advoi-staging.keyteller.com
#
# Branch policy (scripts/www/README.md):
#   - GitHub source of truth: origin/master (and origin/develop kept in sync).
#   - VPS /var/www/advoi/staging may use a local branch name "staging" for the
#     promoted tree; that name has NO origin/staging remote. Never git pull
#     origin/$(git branch --show-current) blindly.
#
# Modes (ADVOI_STAGING_DEPLOY_MODE):
#   pull     — fetch ADVOI_STAGING_DEPLOY_BRANCH from origin, ff-only, compose (default)
#   promote  — develop checkout -> promote-to-staging.sh (when /data/projects/advoi exists)
#   redeploy — compose only; no git (tree already at desired SHA)
#
# Usage:
#   bash /var/www/advoi/deploy-staging.sh
#   ADVOI_STAGING_DEPLOY_MODE=redeploy bash /var/www/advoi/deploy-staging.sh
#   bash /var/www/advoi/deploy-staging.sh --check-only
set -euo pipefail

WWW="/var/www/advoi"
STAGING="${ADVOI_STAGING_PATH:-${WWW}/staging}"
ENV_FILE="${ADVOI_ENV_FILE:-${WWW}/.env.staging}"
COMPOSE_PROJECT="${COMPOSE_PROJECT_NAME:-advoi-staging}"
DEPLOY_MODE="${ADVOI_STAGING_DEPLOY_MODE:-pull}"
DEPLOY_BRANCH="${ADVOI_STAGING_DEPLOY_BRANCH:-master}"
LOCAL_BRANCH="${ADVOI_STAGING_LOCAL_BRANCH:-staging}"
DEV_PATH="${ADVOI_DEV_PATH:-/data/projects/advoi}"
PROMOTE_SCRIPT="${ADVOI_PROMOTE_SCRIPT:-${WWW}/promote-to-staging.sh}"
CHECK_ONLY=0

usage() {
  cat <<'EOF'
Usage: deploy-staging.sh [options]

Options:
  --check-only   Run branch-policy-check only (exit 1 on drift)
  -h, --help     Show this help

Environment:
  ADVOI_STAGING_DEPLOY_MODE   pull | promote | redeploy (default: pull)
  ADVOI_STAGING_DEPLOY_BRANCH Remote branch to deploy (default: master)
  ADVOI_STAGING_LOCAL_BRANCH  Local branch pin after pull (default: staging)
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check-only)
      CHECK_ONLY=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown arg: $1 (branch args removed — use ADVOI_STAGING_DEPLOY_BRANCH)" >&2
      usage >&2
      exit 2
      ;;
  esac
done

warn() {
  echo "WARN: $*" >&2
}

die() {
  echo "ERROR: $*" >&2
  exit 1
}

run_branch_policy_check() {
  local script="${STAGING}/scripts/www/branch-policy-check.sh"
  if [[ -x "${script}" ]]; then
    bash "${script}"
    return $?
  fi
  return 0
}

if [[ "${CHECK_ONLY}" -eq 1 ]]; then
  cd "${STAGING}"
  run_branch_policy_check
  exit $?
fi

case "${DEPLOY_MODE}" in
  promote)
    if [[ -e "${DEV_PATH}/.git" ]] && [[ -x "${PROMOTE_SCRIPT}" || -f "${STAGING}/scripts/www/promote-to-staging.sh" ]]; then
      if [[ -x "${PROMOTE_SCRIPT}" ]]; then
        exec bash "${PROMOTE_SCRIPT}"
      fi
      exec bash "${STAGING}/scripts/www/promote-to-staging.sh"
    fi
    warn "promote mode unavailable (no ${DEV_PATH} or promote script) — falling back to pull ${DEPLOY_BRANCH}"
    DEPLOY_MODE=pull
    ;;
  redeploy)
    echo "==> redeploy mode: skip git, compose only"
    ;;
  pull)
    ;;
  *)
    die "invalid ADVOI_STAGING_DEPLOY_MODE=${DEPLOY_MODE} (use pull|promote|redeploy)"
    ;;
esac

cd "${STAGING}"

if [[ "${DEPLOY_MODE}" == "pull" ]]; then
  echo "==> pull mode: origin/${DEPLOY_BRANCH} -> local ${LOCAL_BRANCH}"
  if ! git remote get-url origin >/dev/null 2>&1; then
    die "staging tree has no origin remote"
  fi
  git fetch origin "${DEPLOY_BRANCH}"
  if ! git show-ref --verify --quiet "refs/remotes/origin/${DEPLOY_BRANCH}"; then
    die "origin/${DEPLOY_BRANCH} does not exist — set ADVOI_STAGING_DEPLOY_BRANCH to master or develop"
  fi
  target_sha="$(git rev-parse "origin/${DEPLOY_BRANCH}")"
  current_sha="$(git rev-parse HEAD)"
  if [[ "${current_sha}" == "${target_sha}" ]]; then
    echo "    already at $(git rev-parse --short HEAD) (origin/${DEPLOY_BRANCH})"
  else
    echo "    update ${current_sha:0:7} -> ${target_sha:0:7}"
  fi
  git checkout -B "${LOCAL_BRANCH}" "origin/${DEPLOY_BRANCH}"
  git merge --ff-only "origin/${DEPLOY_BRANCH}"
  echo "    tree @ $(git rev-parse --short HEAD) on branch ${LOCAL_BRANCH}"
fi

run_branch_policy_check || warn "branch policy check reported drift (deploy continues)"

[[ -f "${ENV_FILE}" ]] || die "missing env file ${ENV_FILE}"

cp "${ENV_FILE}" deploy/.env
chmod 600 deploy/.env

export DEPLOY_MODE=staging
export ENV_FILE=deploy/.env
export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT}"

# shellcheck disable=SC1090
set -a
source deploy/.env
set +a

export ADVOI_ENV="${STAGING}/deploy/.env"
if [[ -x scripts/ensure-deploy-secrets.sh ]]; then
  bash scripts/ensure-deploy-secrets.sh
fi

docker compose -p "${COMPOSE_PROJECT}" \
  -f docker-compose.yml \
  -f deploy/docker-compose.staging.yml \
  -f deploy/docker-compose.www.yml \
  --env-file deploy/.env \
  --profile app \
  up -d --build --remove-orphans

echo "==> STAGING deployed @ $(git rev-parse --short HEAD) ($(git branch --show-current)) from origin/${DEPLOY_BRANCH:-pinned}"

docker compose -p "${COMPOSE_PROJECT}" --env-file deploy/.env ps

HOST="${STOREFRONT_HOST:-advoi-staging.keyteller.com}"
if curl -sf "https://${HOST}/api/health" >/dev/null; then
  curl -sf "https://${HOST}/api/health" && echo ""
else
  curl -k -sI "https://${HOST}" | head -1 || true
  echo "WARN: health check failed (DNS A record for ${HOST}? Traefik cert?)"
fi