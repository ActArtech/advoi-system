#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"
WITH_VOICE="${WITH_VOICE:-true}"
WITH_WEB="${WITH_WEB:-true}"
bash scripts/bootstrap-local-env.sh
docker info >/dev/null 2>&1 || { echo "Start Docker first, or: bash scripts/run-agents-uv.sh"; exit 1; }
SERVICES=(postgres redis advoi-memory-bridge advoi-api advoi-agent-fleet advoi-agent-briefs advoi-agent-review livekit)
[[ "${WITH_VOICE}" == "true" ]] && SERVICES+=(advoi-voice)
[[ "${WITH_WEB}" == "true" ]] && SERVICES+=(advoi-web)
docker compose --profile app --env-file deploy/.env up -d "${SERVICES[@]}"
sleep 10
ADVOI_BASE_URL="http://127.0.0.1:${ADVOI_API_PORT:-8010}" bash scripts/agents-smoke-test.sh || true
echo "Ready: http://127.0.0.1:${ADVOI_WEB_PORT:-3000}"