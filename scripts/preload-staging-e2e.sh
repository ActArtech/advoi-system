#!/usr/bin/env bash
# Preload staging for human Path A E2E: briefs, agent cache, run-six, voice checks.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE="${ADVOI_BASE_URL:-https://advoi.keyteller.com}"

echo "==> ADVoi E2E preload"
echo "    Base URL: $BASE"
echo ""

_curl() {
  curl -sf "$@"
}

echo "==> Agent control"
ctrl="$(_curl "$BASE/api/agents/control" 2>/dev/null || echo '{}')"
echo "    $ctrl"
if echo "$ctrl" | grep -qE '"paused"\s*:\s*true'; then
  echo "==> Agents paused — restarting"
  _curl -X POST "$BASE/api/agents/restart" -H "Content-Type: application/json" -d "{}"
  sleep 3
fi
echo ""

if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx advoi-redis-1; then
  echo "==> Seed briefs (Redis + Postgres + Hindsight best-effort)"
  bash "$ROOT/scripts/seed-advoi-briefs.sh" || echo "    WARN: seed-advoi-briefs had errors (Redis/Postgres may still be set)"
  echo ""
else
  echo "==> Skip seed-advoi-briefs (advoi-redis-1 not on this host)"
  echo ""
fi

echo "==> Prewarm all 6 agents"
pre="$(_curl -X POST "$BASE/api/agents/prewarm" -H "Content-Type: application/json" -d "{}")"
echo "    $pre"
echo ""

echo "==> Run-six (refresh=true, confirmed=true)"
six="$(_curl -X POST "$BASE/api/agents/run-six?refresh=true&confirmed=true" \
  -H "Content-Type: application/json" -d "{}")"
echo "$six" | python3 -c "
import json, sys
d = json.load(sys.stdin)
print('    agents_used:', ', '.join(d.get('agents_used', [])))
spoken = d.get('spoken_summary', '')
print('    spoken:', spoken[:280] + ('...' if len(spoken) > 280 else ''))
" 2>/dev/null || echo "    $six" | head -c 400
echo ""

echo "==> Agent cache"
agents="$(_curl "$BASE/api/agents")"
echo "$agents" | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(f\"    {d.get('ready', 0)}/{d.get('total', 0)} ready\")
" 2>/dev/null || echo "    $agents"
echo ""

echo "==> Health"
echo "    $(_curl "$BASE/api/health")"
echo ""

echo "==> Voice diagnostics"
voice="$(_curl "$BASE/api/diagnostics/voice")"
echo "$voice" | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(f\"    ok={d.get('ok')} llm_key={d.get('llm_key')} bridge={d.get('memory_bridge_mode')}\")
" 2>/dev/null || echo "    $voice"
echo ""

echo "==> Review queue"
rq="$(_curl "$BASE/api/review-queue" 2>/dev/null || echo '{}')"
echo "    $rq"
echo ""

if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx advoi-advoi-voice-1; then
  echo "==> VPS voice verify"
  bash "$ROOT/scripts/verify-vps-voice.sh"
  echo ""
fi

echo "=========================================="
echo "PRELOAD COMPLETE — ready for Path A E2E"
echo "Open: $BASE"
echo "Checklist: docs/operations/E2E-SIGNOFF.md"
echo "=========================================="