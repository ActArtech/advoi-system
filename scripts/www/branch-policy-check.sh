#!/usr/bin/env bash
# Verify ADVoi staging tree matches deploy branch policy.
# Exit 0 when aligned; exit 1 when drift or misconfiguration.
set -euo pipefail

STAGING="${ADVOI_STAGING_PATH:-/var/www/advoi/staging}"
DEPLOY_BRANCH="${ADVOI_STAGING_DEPLOY_BRANCH:-master}"
DEV_PATH="${ADVOI_DEV_PATH:-/data/projects/advoi}"
DEV_BRANCH="${ADVOI_DEV_BRANCH:-develop}"

cd "${STAGING}"

if ! git remote get-url origin >/dev/null 2>&1; then
  echo "FAIL: no origin remote in ${STAGING}" >&2
  exit 1
fi

git fetch origin "${DEPLOY_BRANCH}" "${DEV_BRANCH}" 2>/dev/null || git fetch origin "${DEPLOY_BRANCH}" 2>/dev/null || true

if ! git show-ref --verify --quiet "refs/remotes/origin/${DEPLOY_BRANCH}"; then
  echo "FAIL: origin/${DEPLOY_BRANCH} missing (set ADVOI_STAGING_DEPLOY_BRANCH)" >&2
  exit 1
fi

head_sha="$(git rev-parse HEAD)"
deploy_sha="$(git rev-parse "origin/${DEPLOY_BRANCH}")"
current_branch="$(git branch --show-current)"

echo "staging tree: ${head_sha:0:7} branch=${current_branch}"
echo "origin/${DEPLOY_BRANCH}: ${deploy_sha:0:7}"

if [[ "${head_sha}" != "${deploy_sha}" ]]; then
  echo "FAIL: staging HEAD != origin/${DEPLOY_BRANCH} — run deploy-staging.sh (pull mode)" >&2
  exit 1
fi

if [[ "${current_branch}" == "staging" ]]; then
  if ! git show-ref --verify --quiet refs/remotes/origin/staging 2>/dev/null; then
    echo "OK: local branch 'staging' is intentional (no origin/staging); pinned to origin/${DEPLOY_BRANCH}"
  fi
fi

if [[ -e "${DEV_PATH}/.git" ]]; then
  dev_sha="$(git -C "${DEV_PATH}" rev-parse HEAD 2>/dev/null || echo "")"
  if [[ -n "${dev_sha}" ]] && [[ "${dev_sha}" != "${head_sha}" ]]; then
    echo "WARN: develop checkout ${dev_sha:0:7} != staging ${head_sha:0:7} — run promote-to-staging.sh" >&2
    exit 1
  fi
  echo "develop checkout: aligned @ ${dev_sha:0:7}"
else
  echo "note: no develop checkout at ${DEV_PATH} (www pull mode only)"
fi

echo "branch policy: OK"
exit 0