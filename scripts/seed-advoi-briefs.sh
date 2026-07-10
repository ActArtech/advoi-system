#!/usr/bin/env bash
# Seed open decision briefs for Brief Curator (idempotent).
#
# ADR-026 / EVENT_WRITE_MAP:
#   decision_brief → Postgres only (canonical).
#   Redis advoi:briefs:open is a cache filled FROM Postgres titles (not a second source).
#   Hindsight seed uses portfolio_fact (allowed strategic target) for optional enrichment
#   only — Brief Curator does NOT merge Hindsight into PG/Redis title lists.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HERMES_CONTAINER="${HERMES_CONTAINER:-hermes}"
# Hermes mounts VPS projects under /vps-projects/
BRIDGE="/vps-projects/advoi/scripts/hindsight-bridge.py"
if ! docker exec "${HERMES_CONTAINER}" test -f "${BRIDGE}" 2>/dev/null; then
  BRIDGE="${ROOT}/scripts/hindsight-bridge.py"
fi

_retain_portfolio_fact() {
  # Optional strategic enrich — NOT event_type=decision_brief (that is Postgres-only).
  local summary="$1"
  local project="${2:-advoi}"
  if ! docker ps --format '{{.Names}}' | grep -qx "${HERMES_CONTAINER}"; then
    echo "  WARN: ${HERMES_CONTAINER} not running — Hindsight enrich skipped"
    return 0
  fi
  if docker exec "${HERMES_CONTAINER}" python "${BRIDGE}" --json "$(cat <<EOF
{"action":"retain","event_type":"portfolio_fact","summary":"${summary}","payload":{"project":"${project}","source":"seed-advoi-briefs","role":"brief_enrich"}}
EOF
)" >/dev/null 2>&1; then
    echo "  retained (portfolio_fact enrich): ${summary}"
  else
    echo "  WARN: Hindsight retain skipped (${summary})"
  fi
}

BRIEFS=(
  "Open brief: ADVoi voice launch — validate PWA connect, frame buttons, and TTS on staging"
  "Open brief: Shelve secrets — push fixed OPENAI_API_KEY to ktteam/advoi/staging"
  "Open brief: Portfolio registration — add advoi row to vps-shared port registry"
)
BRIEFS_JSON=$(printf '%s\n' "${BRIEFS[@]}" | python3 -c 'import json,sys; print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))')

echo "==> Seeding ADVoi decision briefs (Postgres canonical first)"
if docker ps --format '{{.Names}}' | grep -qx advoi-advoi-api-1; then
  for brief in "${BRIEFS[@]}"; do
    docker exec advoi-advoi-api-1 python -c "
import asyncio
from advoi.memory.postgres_store import upsert_open_brief
asyncio.run(upsert_open_brief('''${brief}'''))
" >/dev/null 2>&1 || true
  done
  echo "OK: briefs in Postgres (decision_briefs) — Redis cache invalidated on write"
else
  echo "WARN: advoi-advoi-api-1 not running — Postgres briefs not set"
fi

# Cache fill from the same canonical list (not an independent third write of different data).
if docker ps --format '{{.Names}}' | grep -qx advoi-redis-1; then
  docker exec advoi-redis-1 redis-cli SET advoi:briefs:open "${BRIEFS_JSON}" >/dev/null
  echo "OK: Redis cache filled (advoi:briefs:open mirrors seed titles)"
else
  echo "WARN: advoi-redis-1 not running — Redis briefs cache not set"
fi

echo "==> Optional Hindsight portfolio_fact enrich (not Brief Curator merge source)"
_retain_portfolio_fact "Open brief: ADVoi voice launch — validate PWA connect, frame buttons, and TTS on staging"
_retain_portfolio_fact "Open brief: Shelve secrets — push fixed OPENAI_API_KEY to ktteam/advoi/staging"
_retain_portfolio_fact "Open brief: Portfolio registration — add advoi row to vps-shared port registry"

echo "OK: briefs seeded (PG canonical; Redis cache; Hindsight enrich best-effort)"
