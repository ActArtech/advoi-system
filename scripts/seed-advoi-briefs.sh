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
BRIEFS_JSON='["Open brief: ADVoi voice launch — validate PWA connect, frame buttons, and TTS on staging","Open brief: Shelve secrets — push fixed OPENAI_API_KEY to ktteam/advoi/staging","Open brief: Portfolio registration — add advoi row to vps-shared port registry"]'
if docker ps --format '{{.Names}}' | grep -qx advoi-redis-1; then
  docker exec advoi-redis-1 redis-cli SET advoi:briefs:open "${BRIEFS_JSON}" >/dev/null
  echo "OK: briefs in Redis (advoi:briefs:open)"
else
  echo "WARN: advoi-redis-1 not running — Redis briefs not set"
fi
echo "OK: briefs seeded (Hindsight recall may take a few seconds to index)"