#!/usr/bin/env bash
# Staging voice journey smoke — run on VPS or against public URL.
set -euo pipefail

BASE="${ADVOI_BASE_URL:-https://advoi.keyteller.com}"
FAIL=0

check() {
  local name="$1"
  local url="$2"
  local expect="${3:-ok}"
  echo -n "==> ${name} ... "
  if resp=$(curl -sf "${url}" 2>/dev/null); then
    if echo "${resp}" | grep -q "${expect}"; then
      echo "OK"
    else
      echo "FAIL (missing ${expect})"
      FAIL=1
    fi
  else
    echo "FAIL (HTTP)"
    FAIL=1
  fi
}

check_post() {
  local name="$1"
  local url="$2"
  local body="${3:-"{}"}"
  local expect="${4:-spoken_summary}"
  echo -n "==> ${name} ... "
  if resp=$(curl -sf -X POST -H "Content-Type: application/json" -d "${body}" "${url}" 2>/dev/null); then
    if echo "${resp}" | grep -q "${expect}"; then
      echo "OK"
    else
      echo "FAIL"
      FAIL=1
    fi
  else
    echo "FAIL (HTTP)"
    FAIL=1
  fi
}

check "health" "${BASE}/api/health" "voice-pwa-2"
check "diagnostics" "${BASE}/api/diagnostics/voice" '"checks"'
check "frames" "${BASE}/api/frames" "fleet_status"
check "agents" "${BASE}/api/agents" "fleet-scout"
check_post "token" "${BASE}/api/livekit/token" "{}" '"token"'
check_post "frame fleet" "${BASE}/api/frames/fleet_status/run" "{}"
check_post "frame briefs" "${BASE}/api/frames/open_briefs/run" "{}"
check_post "frame review" "${BASE}/api/frames/queue_deep_review/run" '{"confirmed":true}'

if [[ "${FAIL}" -eq 0 ]]; then
  echo "All voice journey checks passed."
  exit 0
fi
echo "Some checks failed."
exit 1