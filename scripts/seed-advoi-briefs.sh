#!/usr/bin/env bash
# Seed Hindsight with open decision briefs for Brief Curator frame (idempotent).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HERMES_CONTAINER="${HERMES_CONTAINER:-hermes}"
# Hermes mounts VPS projects under /vps-projects/
BRIDGE="/vps-projects/advoi/scripts/hindsight-bridge.py"
if ! docker exec "${HERMES_CONTAINER}" test -f "${BRIDGE}" 2>/dev/null; then
  BRIDGE="${ROOT}/scripts/hindsight-bridge.py"
fi

if ! docker ps --format '{{.Names}}' | grep -qx "${HERMES_CONTAINER}"; then
  echo "ERROR: ${HERMES_CONTAINER} not running" >&2
  exit 1
fi

_retain() {
  local summary="$1"
  local project="${2:-advoi}"
  docker exec "${HERMES_CONTAINER}" python "${BRIDGE}" --json "$(cat <<EOF
{"action":"retain","event_type":"decision_brief","summary":"${summary}","payload":{"project":"${project}","source":"seed-advoi-briefs"}}
EOF
)" >/dev/null
  echo "  retained: ${summary}"
}

echo "==> Seeding ADVoi decision briefs into Hindsight"
_retain "Open brief: ADVoi voice launch — validate PWA connect, frame buttons, and TTS on staging"
_retain "Open brief: Shelve secrets — push fixed OPENAI_API_KEY to ktteam/advoi/staging"
_retain "Open brief: Portfolio registration — add advoi row to vps-shared port registry"
BRIEFS=(
  "Open brief: ADVoi voice launch — validate PWA connect, frame buttons, and TTS on staging"
  "Open brief: Shelve secrets — push fixed OPENAI_API_KEY to ktteam/advoi/staging"
  "Open brief: Portfolio registration — add advoi row to vps-shared port registry"
)
BRIEFS_JSON=$(printf '%s\n' "${BRIEFS[@]}" | python3 -c 'import json,sys; print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))')
if docker ps --format '{{.Names}}' | grep -qx advoi-redis-1; then
  docker exec advoi-redis-1 redis-cli SET advoi:briefs:open "${BRIEFS_JSON}" >/dev/null
  echo "OK: briefs in Redis (advoi:briefs:open)"
else
  echo "WARN: advoi-redis-1 not running — Redis briefs not set"
fi
if docker ps --format '{{.Names}}' | grep -qx advoi-advoi-api-1; then
  for brief in "${BRIEFS[@]}"; do
    docker exec advoi-advoi-api-1 python -c "
import asyncio
from advoi.memory.postgres_store import upsert_open_brief
asyncio.run(upsert_open_brief('''${brief}'''))
" >/dev/null 2>&1 || true
  done
  echo "OK: briefs in Postgres (decision_briefs)"
fi
echo "OK: briefs seeded (Hindsight recall may take a few seconds to index)"