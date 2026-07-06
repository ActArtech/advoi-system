#!/usr/bin/env bash
# Clone ADVoi to /opt/advoi — NEVER overwrites other projects or existing /opt/advoi data.
set -euo pipefail

SLUG=advoi
OPT_DIR="/opt/${SLUG}"
REMOTE="${ADVOI_REMOTE:-git@github-advoi:ActArtech/advoi-system.git}"
BRANCH="${ADVOI_BRANCH:-master}"

echo "==> ADVoi bootstrap (clone-only policy)"
echo "    Target: ${OPT_DIR}"
echo "    Remote: ${REMOTE}"
echo "    Will NOT touch: /opt/firstmate, /opt/firstmate-fleet, /opt/aether, or any other /opt/* project"

if [[ -d "${OPT_DIR}/.git" ]]; then
  echo "==> Existing git checkout — fast-forward pull only"
  cd "${OPT_DIR}"
  git fetch origin "${BRANCH}"
  git merge --ff-only "origin/${BRANCH}"
elif [[ -d "${OPT_DIR}" ]] && [[ -n "$(ls -A "${OPT_DIR}" 2>/dev/null)" ]]; then
  echo "ERROR: ${OPT_DIR} exists but is not a git repo."
  echo "Refusing to overwrite. Move or rename manually, then re-run."
  exit 1
else
  echo "==> Fresh clone into ${OPT_DIR}"
  sudo mkdir -p "${OPT_DIR}"
  sudo chown deploy:deploy "${OPT_DIR}"
  git clone --branch "${BRANCH}" "${REMOTE}" "${OPT_DIR}"
  cd "${OPT_DIR}"
fi

chmod +x scripts/*.sh 2>/dev/null || true
mkdir -p deploy data state

if [[ ! -f deploy/.env ]]; then
  if [[ -f deploy/.env.staging.example ]]; then
    cp deploy/.env.staging.example deploy/.env
    echo "==> Created deploy/.env from staging example — edit secrets before app profile"
  fi
  if [[ -f /opt/shelve/scripts/shelve-pull-deploy.sh ]] && [[ -f shelve.json ]]; then
    # shellcheck source=/opt/shelve/scripts/shelve-pull-deploy.sh
    source /opt/shelve/scripts/shelve-pull-deploy.sh
    shelve_pull_deploy "${OPT_DIR}" || true
  fi
fi

if [[ -f deploy/.env ]]; then
  chmod 600 deploy/.env
fi

echo "==> Deploy infrastructure (postgres + redis only)"
bash scripts/vps-deploy.sh

echo ""
echo "Done. Next:"
echo "  bash scripts/vps-staging-check.sh"
echo "  Edit deploy/.env — LIVEKIT_*, FIRSTMATE bridge vars"
echo "  When ready: DEPLOY_MODE=staging bash scripts/vps-deploy.sh --profile app"