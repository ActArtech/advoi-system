#!/usr/bin/env bash
# Push corrected OPENAI_API_KEY from clapart into Shelve staging (run on VPS).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

bash "${ROOT}/scripts/ensure-deploy-secrets.sh"

if [[ ! -f /opt/shelve/scripts/shelve-push-deploy.sh ]] && ! command -v npx >/dev/null 2>&1; then
  echo "WARN: cannot push to Shelve — fix deploy/.env locally only"
  exit 0
fi

if command -v npx >/dev/null 2>&1 && [[ -f "${ROOT}/shelve.json" ]]; then
  echo "==> Pushing fixed deploy/.env to Shelve staging"
  npx --yes @shelve/cli --non-interactive --yes push --env staging
  echo "OK: Shelve updated"
fi