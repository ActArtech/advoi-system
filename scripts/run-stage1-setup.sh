#!/usr/bin/env bash
# Run Stage 1 setup tasks in parallel (local validation + optional VPS).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

RUN_VPS="${RUN_VPS:-false}"
VPS_HOST="${VPS_HOST:-deploy@187.77.140.216}"

echo "==> Stage 1 setup — parallel agents"

pids=()

bash scripts/aether-bootstrap.sh &
pids+=($!)

if command -v uv >/dev/null 2>&1; then
  (uv sync --extra voice && uv run pytest tests/ -q) &
  pids+=($!)
fi

if [[ -f web/package.json ]]; then
  (cd web && npm install --prefer-offline 2>/dev/null && npm run build) &
  pids+=($!)
fi

if [[ "${RUN_VPS}" == "true" ]]; then
  (
    ssh -o ConnectTimeout=15 "${VPS_HOST}" 'cd /opt/advoi && git pull origin master && bash scripts/port-registry-apply.sh && bash scripts/aether-bootstrap.sh'
  ) &
  pids+=($!)
fi

fail=0
for pid in "${pids[@]}"; do
  if ! wait "${pid}"; then
    fail=1
  fi
done

if [[ "${fail}" -ne 0 ]]; then
  echo "ERROR: one or more Stage 1 setup tasks failed" >&2
  exit 1
fi

echo "==> Stage 1 setup complete"
echo "Next: set LIVEKIT_* in deploy/.env, then: DEPLOY_MODE=staging bash scripts/vps-deploy.sh --profile app"