#!/usr/bin/env bash
# Automated pre-checks before human E2E sign-off (docs/operations/E2E-SIGNOFF.md).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

BASE="${ADVOI_BASE_URL:-https://advoi.keyteller.com}"
FAIL=0

echo "==> ADVoi staging sign-off pre-check"
echo "    Base URL: ${BASE}"
echo ""

run_check() {
  local name="$1"
  shift
  echo "==> ${name}"
  if "$@"; then
    echo "    OK"
  else
    echo "    FAIL"
    FAIL=1
  fi
  echo ""
}

run_check "voice-smoke-test" env ADVOI_BASE_URL="${BASE}" bash scripts/voice-smoke-test.sh

echo "==> latency diagnostics"
if resp=$(curl -sf "${BASE}/api/diagnostics/latency" 2>/dev/null); then
  echo "${resp}" | python3 -c "
import json, sys
d = json.load(sys.stdin)
t = d.get('timings_ms', {})
print(f\"    health_ms={t.get('health_ms')} token_ms={t.get('token_ms')} frame_run_ms={t.get('frame_run_ms')}\")
print(f\"    intent_ms={t.get('intent_ms')} respond_ms={t.get('respond_ms')} api_voice_path_ms={t.get('api_voice_path_ms')}\")
print(f\"    sla_target_ms={d.get('sla_target_ms')} sla_ok={d.get('sla_ok')}\")
sys.exit(0 if d.get('ok') else 1)
" || FAIL=1
  echo "    OK"
else
  echo "    FAIL (HTTP)"
  FAIL=1
fi
echo ""

echo "==> review-queue"
if curl -sf "${BASE}/api/review-queue" | grep -q '"pending"'; then
  echo "    OK"
else
  echo "    FAIL"
  FAIL=1
fi
echo ""

echo "==> agents cache"
if resp=$(curl -sf "${BASE}/api/agents" 2>/dev/null); then
  echo "${resp}" | python3 -c "
import json, sys
d = json.load(sys.stdin)
ready = d.get('ready', 0)
total = d.get('total', 0)
print(f\"    {ready}/{total} agents ready, all_ready={d.get('all_ready')}\")
sys.exit(0 if ready == total and total >= 3 else 1)
" || FAIL=1
  echo "    OK"
else
  echo "    FAIL (HTTP)"
  FAIL=1
fi
echo ""

if [[ -f scripts/agents-smoke-test.sh ]]; then
  ADVOI_BASE_URL="${BASE}" run_check "agents-smoke-test" bash scripts/agents-smoke-test.sh
fi

if [[ "${FAIL}" -eq 0 ]]; then
  echo "=========================================="
  echo "AUTOMATED PRE-CHECKS PASSED"
  echo "Next: human E2E on phone (docs/operations/E2E-SIGNOFF.md)"
  echo "  1. Open ${BASE}"
  echo "  2. Connect voice, allow mic"
  echo "  3. Hear greeting, tap frames A/B/C"
  echo "  4. Say 'queue review' then 'yes'"
  echo "=========================================="
  exit 0
fi

echo "PRE-CHECKS FAILED — fix before human sign-off."
echo "VPS recovery: ADVOI_SHELVE_PULL=false DEPLOY_MODE=staging bash scripts/repair-vps-env.sh"
exit 1