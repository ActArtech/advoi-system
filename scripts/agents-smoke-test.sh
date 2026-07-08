#!/usr/bin/env bash
# On Windows: use agents-smoke-test.ps1 (PowerShell env vars do not reach WSL bash).
set -euo pipefail
BASE="${ADVOI_BASE_URL:-https://advoi.keyteller.com}"
FAIL=0

expect_agent() {
  local agent_id="$1"
  echo -n "==> agent ${agent_id} ... "
  resp="$(curl -sf "${BASE}/api/agents" 2>/dev/null || true)"
  if [[ -z "${resp}" ]]; then echo "FAIL"; FAIL=1; return; fi
  if echo "${resp}" | python3 -c "
import json, sys
agents = json.load(sys.stdin).get('agents', [])
match = next((a for a in agents if a.get('id') == sys.argv[1]), None)
sys.exit(0 if match else 1)
" "${agent_id}"; then
    if echo "${resp}" | grep -q "last_run"; then echo "OK (cached)"; else echo "WARN (no cache yet)"; fi
  else
    echo "FAIL"
    FAIL=1
  fi
}

check_post() {
  local name="$1" url="$2" body="${3:-"{}"}"
  local attempt
  echo -n "==> ${name} ... "
  for attempt in 1 2 3; do
    if curl -sf -X POST -H "Content-Type: application/json" -d "${body}" "${url}" >/dev/null 2>&1; then
      echo OK
      return
    fi
    [[ "${attempt}" -lt 3 ]] && sleep 2
  done
  echo FAIL
  FAIL=1
}

echo "==> Multi-agent smoke (${BASE})"
curl -sf "${BASE}/api/health" >/dev/null || { echo "FAIL: API down"; exit 1; }
check_post "fleet" "${BASE}/api/frames/fleet_status/run"
check_post "briefs" "${BASE}/api/frames/open_briefs/run"
check_post "review" "${BASE}/api/frames/queue_deep_review/run" '{"confirmed":true}'
expect_agent fleet-scout
expect_agent brief-curator
expect_agent review-queue
[[ "${FAIL}" -eq 0 ]] && echo "All passed." && exit 0
echo "Some failed."; exit 1