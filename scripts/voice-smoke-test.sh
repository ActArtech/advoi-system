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

echo -n "==> diagnostics llm_key ... "
if resp=$(curl -sf "${BASE}/api/diagnostics/voice" 2>/dev/null); then
  if echo "${resp}" | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if d.get('checks',{}).get('llm_key') else 1)"; then
    echo "OK"
  else
    echo "FAIL (llm_key false — advoi-voice needs OPENROUTER_API_KEY or OPENAI_API_KEY)"
    FAIL=1
  fi
else
  echo "FAIL (HTTP)"
  FAIL=1
fi
check "frames" "${BASE}/api/frames" "fleet_status"
check "agents" "${BASE}/api/agents" "fleet-scout"
check_post "token" "${BASE}/api/livekit/token" "{}" '"token"'
check_post "voice intent fleet" "${BASE}/api/voice/intent" '{"transcript":"Give me a fleet status update","preview":true}' '"frame_id":"fleet_status"'
check_post "voice intent chat" "${BASE}/api/voice/intent" '{"transcript":"How are you today?"}' '"action":"chat"'
check_post "voice intent review" "${BASE}/api/voice/intent" '{"transcript":"queue deep review"}' '"frame_id":"queue_deep_review"'
check_post "voice intent review confirm" "${BASE}/api/voice/intent" '{"transcript":"queue deep review"}' '"confirmed":false'
check_post "frame fleet" "${BASE}/api/frames/fleet_status/run" "{}"
check_post "frame briefs" "${BASE}/api/frames/open_briefs/run" "{}"
check_post "frame review" "${BASE}/api/frames/queue_deep_review/run" '{"confirmed":true}'
check_post "voice respond" "${BASE}/api/voice/respond" '{"transcript":"What briefs are open?"}' '"spoken"'
check "frame intents" "${BASE}/api/frames" "voice_prompt"

for frame_id in fleet_status open_briefs queue_deep_review; do
  echo -n "==> intent ${frame_id} ... "
  if resp=$(curl -sf "${BASE}/api/frames" 2>/dev/null); then
    if echo "${resp}" | grep -q "\"id\": \"${frame_id}\"" && echo "${resp}" | grep -q "voice_prompt"; then
      echo "OK"
    else
      echo "FAIL"
      FAIL=1
    fi
  else
    echo "FAIL (HTTP)"
    FAIL=1
  fi
done

echo -n "==> latency ... "
if resp=$(curl -sf "${BASE}/api/diagnostics/latency" 2>/dev/null); then
  if echo "${resp}" | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if d.get('ok') and d['timings_ms'].get('respond_ms') is not None else 1)"; then
    sla=$(echo "${resp}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('sla_ok'))")
    path_ms=$(echo "${resp}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['timings_ms'].get('api_voice_path_ms'))")
    echo "OK (api_voice_path_ms=${path_ms}, sla_ok=${sla})"
  else
    echo "FAIL"
    FAIL=1
  fi
else
  echo "FAIL (HTTP)"
  FAIL=1
fi

echo -n "==> review-queue ... "
if curl -sf "${BASE}/api/review-queue" | grep -q '"pending"'; then
  echo "OK"
else
  echo "FAIL"
  FAIL=1
fi

if [[ "${FAIL}" -eq 0 ]]; then
  echo "All voice journey checks passed."
  exit 0
fi
echo "Some checks failed."
exit 1