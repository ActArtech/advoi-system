#!/usr/bin/env bash
# Run API + all 3 specialist agents without Docker (mock mode).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

API_PORT="${ADVOI_API_PORT:-8010}"

bash scripts/bootstrap-local-env.sh

export ADVOI_FRAME_MOCK=true
export ADVOI_AGENT_INTERVAL_SECS="${ADVOI_AGENT_INTERVAL_SECS:-30}"
export ADVOI_ALLOWED_ORIGINS="http://localhost:3000,http://127.0.0.1:3000"
export REDIS_URL="${REDIS_URL:-redis://127.0.0.1:6382/0}"

cleanup() {
  kill "${API_PID:-}" "${AGENT_PID:-}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "==> API on :${API_PORT}"
uv run uvicorn advoi.api.app:app --host 127.0.0.1 --port "${API_PORT}" &
API_PID=$!

echo "==> Agent supervisor (fleet-scout, brief-curator, review-queue)"
uv sync --quiet
uv run advoi-supervisor &
AGENT_PID=$!

sleep 4
if curl -sf "http://127.0.0.1:${API_PORT}/api/health" >/dev/null; then
  echo "OK: API healthy"
else
  echo "WARN: API not ready yet"
fi

echo ""
echo "Smoke: ADVOI_BASE_URL=http://127.0.0.1:${API_PORT} bash scripts/agents-smoke-test.sh"
echo "Press Ctrl+C to stop"
wait