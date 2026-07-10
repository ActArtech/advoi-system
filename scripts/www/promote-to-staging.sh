#!/usr/bin/env bash
# Promote develop checkout → www staging tree (/var/www/advoi/staging).
#
# Idempotent: re-running when staging already matches develop tip is a no-op for
# git (still redeploys unless --skip-compose). Safe to re-run after partial fails.
#
# Operator prerequisite (GAP-013):
#   SSH host-key / known_hosts for deploy@VPS must be fixed before remote
#   promote or automated SSH deploy. This script itself runs ON the VPS (or a
#   machine that already has the paths). Crewmate does not SSH to the VPS.
#
# Required / documented env (defaults match docs/VPS-SETUP.md):
#   ADVOI_DEV_PATH       develop git checkout (default: /data/projects/advoi)
#   ADVOI_STAGING_PATH   staging tree        (default: /var/www/advoi/staging)
#   ADVOI_DEPLOY_USER    expected OS user    (default: deploy)
#   ADVOI_DEV_BRANCH     source branch       (default: develop)
#   ADVOI_STAGING_BRANCH staging branch name (default: staging)
#   ADVOI_ENV_FILE       compose env file    (default: deploy/.env under staging)
#   ADVOI_WWW_PROJECT    compose project     (default: advoi-staging)
#   ADVOI_BASE_URL       post-promote smoke  (default: https://advoi-staging.keyteller.com)
#
# Usage (on VPS as deploy):
#   bash scripts/www/promote-to-staging.sh
#   bash scripts/www/promote-to-staging.sh --dry-run
#   bash /var/www/advoi/promote-to-staging.sh   # host install of this file
#
# Install host entrypoint (once, optional):
#   install -m 755 scripts/www/promote-to-staging.sh /var/www/advoi/promote-to-staging.sh
#
# No live cutover. No SSH secrets. Does not touch /var/www/advoi/live.

set -euo pipefail

DRY_RUN=0
SKIP_COMPOSE=0
SKIP_SMOKE=0
FETCH=1

usage() {
  cat <<'EOF'
Usage: promote-to-staging.sh [options]

Idempotent promote: develop checkout → /var/www/advoi/staging (+ optional compose).

Options:
  -n, --dry-run       Print actions only; do not mutate git or compose
      --skip-compose  Update staging git tree only (no docker compose)
      --skip-smoke    Skip post-deploy T2 smoke curl
      --no-fetch      Do not git fetch (use local develop tip as-is)
  -h, --help          Show this help

Environment (see scripts/www/README.md):
  ADVOI_DEV_PATH ADVOI_STAGING_PATH ADVOI_DEPLOY_USER
  ADVOI_DEV_BRANCH ADVOI_STAGING_BRANCH ADVOI_ENV_FILE
  ADVOI_WWW_PROJECT ADVOI_BASE_URL

Prerequisite: GAP-013 SSH host-key fix (operator), before remote promote.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -n|--dry-run)
      DRY_RUN=1
      shift
      ;;
    --skip-compose)
      SKIP_COMPOSE=1
      shift
      ;;
    --skip-smoke)
      SKIP_SMOKE=1
      shift
      ;;
    --no-fetch)
      FETCH=0
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown arg: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

DEV_PATH="${ADVOI_DEV_PATH:-/data/projects/advoi}"
STAGING_PATH="${ADVOI_STAGING_PATH:-/var/www/advoi/staging}"
DEPLOY_USER="${ADVOI_DEPLOY_USER:-deploy}"
DEV_BRANCH="${ADVOI_DEV_BRANCH:-develop}"
STAGING_BRANCH="${ADVOI_STAGING_BRANCH:-staging}"
WWW_PROJECT="${ADVOI_WWW_PROJECT:-advoi-staging}"
SMOKE_BASE="${ADVOI_BASE_URL:-https://advoi-staging.keyteller.com}"

run() {
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo "DRY-RUN: $*"
    return 0
  fi
  "$@"
}

log() {
  echo "==> $*"
}

warn() {
  echo "WARN: $*" >&2
}

die() {
  echo "ERROR: $*" >&2
  exit 1
}

# --- preflight ---------------------------------------------------------------

log "ADVoi promote develop → staging (www tier)"
echo "    dev:     ${DEV_PATH} (branch ${DEV_BRANCH})"
echo "    staging: ${STAGING_PATH} (branch ${STAGING_BRANCH})"
echo "    user:    expected ${DEPLOY_USER} (actual: $(id -un))"
if [[ "${DRY_RUN}" -eq 1 ]]; then
  echo "    mode:    dry-run"
fi

if [[ "$(id -un)" != "${DEPLOY_USER}" ]]; then
  warn "running as $(id -un), expected ${DEPLOY_USER} — continue only if intentional"
fi

# Accept regular repo (.git dir) and linked worktrees (.git file).
if [[ ! -e "${DEV_PATH}/.git" ]] || ! git -C "${DEV_PATH}" rev-parse --git-dir >/dev/null 2>&1; then
  die "develop checkout missing or not a git repo: ${DEV_PATH}"
fi
[[ -r "${DEV_PATH}" ]] || die "cannot read develop path: ${DEV_PATH}"

# --- develop tip -------------------------------------------------------------

log "Resolve develop tip at ${DEV_PATH}"
pushd "${DEV_PATH}" >/dev/null

current_branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo DETACHED)"
if [[ "${current_branch}" != "${DEV_BRANCH}" ]]; then
  warn "develop path is on '${current_branch}', expected '${DEV_BRANCH}' — using local tip"
fi

if [[ "${FETCH}" -eq 1 ]]; then
  if git remote get-url origin >/dev/null 2>&1; then
    run git fetch origin "${DEV_BRANCH}"
    if git show-ref --verify --quiet "refs/remotes/origin/${DEV_BRANCH}"; then
      if [[ "${current_branch}" == "${DEV_BRANCH}" ]]; then
        run git merge --ff-only "origin/${DEV_BRANCH}" || die "ff-only failed on ${DEV_BRANCH}; resolve manually"
      else
        warn "not on ${DEV_BRANCH}; skip ff-only merge (tip remains local HEAD)"
      fi
    fi
  else
    warn "no origin remote — promote uses local HEAD only"
  fi
fi

DEV_SHA="$(git rev-parse HEAD)"
DEV_SHORT="$(git rev-parse --short HEAD)"
log "develop tip: ${DEV_SHA} (${DEV_SHORT})"

popd >/dev/null

# --- staging tree ------------------------------------------------------------

is_git_checkout() {
  local path="$1"
  [[ -e "${path}/.git" ]] && git -C "${path}" rev-parse --git-dir >/dev/null 2>&1
}

ensure_staging_clone() {
  if is_git_checkout "${STAGING_PATH}"; then
    return 0
  fi
  if [[ -e "${STAGING_PATH}" ]] && [[ -n "$(ls -A "${STAGING_PATH}" 2>/dev/null || true)" ]]; then
    die "${STAGING_PATH} exists but is not a git repo (clone-only policy; no rsync overwrite)"
  fi
  log "Fresh clone into ${STAGING_PATH} from ${DEV_PATH}"
  parent="$(dirname "${STAGING_PATH}")"
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo "DRY-RUN: mkdir -p ${parent}"
    echo "DRY-RUN: git clone ${DEV_PATH} ${STAGING_PATH}"
    return 0
  fi
  mkdir -p "${parent}"
  # Local path clone preserves objects; no GitHub token/SSH secrets required.
  git clone "${DEV_PATH}" "${STAGING_PATH}"
}

ensure_staging_clone

if [[ "${DRY_RUN}" -eq 1 ]] && ! is_git_checkout "${STAGING_PATH}"; then
  log "dry-run: skip staging git update (tree would be created at ${STAGING_PATH})"
else
  pushd "${STAGING_PATH}" >/dev/null

  STAGING_SHA="$(git rev-parse HEAD 2>/dev/null || echo "")"
  if [[ -n "${STAGING_SHA}" ]] && [[ "${STAGING_SHA}" == "${DEV_SHA}" ]]; then
    log "staging already at ${DEV_SHORT} — content no-op (idempotent)"
  else
    log "Update staging ${STAGING_SHA:-none} → ${DEV_SHA}"
    # Pull objects from the develop checkout (no GitHub credentials required).
    if is_git_checkout "${DEV_PATH}"; then
      if [[ "${DRY_RUN}" -eq 1 ]]; then
        echo "DRY-RUN: git fetch ${DEV_PATH} +HEAD:refs/remotes/dev-src/HEAD"
      else
        git fetch "${DEV_PATH}" "+HEAD:refs/remotes/dev-src/HEAD" \
          || die "cannot fetch develop tip into staging from ${DEV_PATH}"
      fi
    elif git remote get-url origin >/dev/null 2>&1 && [[ "${FETCH}" -eq 1 ]]; then
      run git fetch origin || warn "git fetch origin failed — continuing with local objects"
    fi
    if [[ "${DRY_RUN}" -eq 0 ]] && ! git cat-file -e "${DEV_SHA}^{commit}" 2>/dev/null; then
      die "staging missing commit ${DEV_SHA} after fetch"
    fi
  fi

  # Always pin local branch name to staging @ develop tip (even when SHA matches).
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo "DRY-RUN: git checkout -B ${STAGING_BRANCH} ${DEV_SHA}"
  else
    git checkout -B "${STAGING_BRANCH}" "${DEV_SHA}"
    log "staging now at $(git rev-parse --short HEAD) on ${STAGING_BRANCH}"
  fi

  popd >/dev/null
fi

# --- compose (staging tree only; never live) ---------------------------------

if [[ "${SKIP_COMPOSE}" -eq 1 ]]; then
  log "skip compose (--skip-compose)"
else
  ENV_FILE="${ADVOI_ENV_FILE:-${STAGING_PATH}/deploy/.env}"
  COMPOSE_WWW="${STAGING_PATH}/compose.www.yml"
  COMPOSE_BASE="${STAGING_PATH}/docker-compose.yml"
  COMPOSE_STAGING="${STAGING_PATH}/deploy/docker-compose.staging.yml"

  if [[ ! -f "${COMPOSE_BASE}" ]]; then
    die "missing ${COMPOSE_BASE}"
  fi
  if [[ ! -f "${COMPOSE_STAGING}" ]]; then
    die "missing ${COMPOSE_STAGING}"
  fi
  if [[ ! -f "${COMPOSE_WWW}" ]]; then
    warn "missing ${COMPOSE_WWW} — promoting git only; add compose.www.yml for www overlay"
    SKIP_COMPOSE=1
  fi
fi

if [[ "${SKIP_COMPOSE}" -eq 0 ]]; then
  ENV_FILE="${ADVOI_ENV_FILE:-${STAGING_PATH}/deploy/.env}"
  if [[ ! -f "${ENV_FILE}" ]]; then
    example="${STAGING_PATH}/deploy/.env.staging.example"
    if [[ -f "${example}" ]]; then
      log "Create ${ENV_FILE} from staging example (edit secrets before app traffic)"
      run cp "${example}" "${ENV_FILE}"
      # shellcheck disable=SC2016
      run sed -i 's/change-me-advoi-pg/advoi/' "${ENV_FILE}" 2>/dev/null || true
    else
      die "missing ${ENV_FILE} and no deploy/.env.staging.example"
    fi
  fi

  # Ensure staging hostname defaults when still on live template values.
  if [[ -f "${ENV_FILE}" ]] && [[ "${DRY_RUN}" -eq 0 ]]; then
    if grep -qE '^STOREFRONT_HOST=advoi\.keyteller\.com$' "${ENV_FILE}" 2>/dev/null; then
      warn "STOREFRONT_HOST is live host — set advoi-staging.keyteller.com for www staging"
    fi
  fi

  log "Compose up project ${WWW_PROJECT} from ${STAGING_PATH}"
  # COMPOSE_PROJECT_NAME isolates staging from legacy name: advoi and future live.
  export COMPOSE_PROJECT_NAME="${WWW_PROJECT}"
  export ADVOI_WWW_TIER=staging
  export ADVOI_WWW_PROJECT="${WWW_PROJECT}"

  compose_cmd=(
    docker compose
    --env-file "${ENV_FILE}"
    -f "${STAGING_PATH}/docker-compose.yml"
    -f "${STAGING_PATH}/deploy/docker-compose.staging.yml"
    -f "${STAGING_PATH}/compose.www.yml"
    --profile app
  )

  # Optional Letta / OTel overlays (same pattern as scripts/staging-redeploy.sh).
  if grep -qE '^LETTA_ENABLED=(true|1|yes)' "${ENV_FILE}" 2>/dev/null; then
    if [[ -f "${STAGING_PATH}/deploy/docker-compose.letta.yml" ]]; then
      compose_cmd+=(-f "${STAGING_PATH}/deploy/docker-compose.letta.yml")
      log "Letta overlay enabled"
    fi
  fi

  run "${compose_cmd[@]}" build advoi-api advoi-web advoi-voice
  run "${compose_cmd[@]}" up -d \
    advoi-api advoi-web advoi-voice \
    advoi-agent-fleet advoi-agent-briefs advoi-agent-review \
    advoi-agent-systems advoi-agent-memory advoi-agent-guardian \
    redis postgres advoi-memory-bridge livekit

  if grep -qE '^OTEL_ENABLED=(true|1|yes)' "${ENV_FILE}" 2>/dev/null; then
    log "OTEL_ENABLED — start otel-collector (profile observability)"
    run docker compose \
      --env-file "${ENV_FILE}" \
      -f "${STAGING_PATH}/docker-compose.yml" \
      -f "${STAGING_PATH}/deploy/docker-compose.staging.yml" \
      -f "${STAGING_PATH}/compose.www.yml" \
      --profile observability \
      up -d otel-collector
  fi
fi

# --- smoke -------------------------------------------------------------------

if [[ "${SKIP_SMOKE}" -eq 1 ]]; then
  log "skip smoke (--skip-smoke)"
elif [[ "${DRY_RUN}" -eq 1 ]]; then
  echo "DRY-RUN: curl -sf ${SMOKE_BASE}/api/health"
  if [[ -x "${STAGING_PATH}/scripts/t2-staging-smoke.sh" ]]; then
    echo "DRY-RUN: ADVOI_BASE_URL=${SMOKE_BASE} bash ${STAGING_PATH}/scripts/t2-staging-smoke.sh"
  fi
else
  log "Smoke ${SMOKE_BASE}/api/health"
  if curl -sf --max-time 20 "${SMOKE_BASE}/api/health" >/dev/null; then
    echo "    health OK"
  else
    warn "health check failed (stack may still be starting)"
  fi
  if [[ -f "${STAGING_PATH}/scripts/t2-staging-smoke.sh" ]]; then
    log "T2 staging smoke"
    if ADVOI_BASE_URL="${SMOKE_BASE}" bash "${STAGING_PATH}/scripts/t2-staging-smoke.sh"; then
      echo "    T2 smoke passed"
    else
      die "T2 smoke failed — see scripts/t2-staging-smoke.sh"
    fi
  fi
fi

log "Done. staging tree ${STAGING_PATH} @ ${DEV_SHORT}"
echo "    No live cutover performed. Live remains at /var/www/advoi/live until explicit promote-to-live."
echo "    GAP-013: if this was intended via remote SSH and failed earlier, fix host keys first."
