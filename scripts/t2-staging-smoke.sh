#!/usr/bin/env bash
# T2 post-deploy staging API smoke for ADVoi.
#
# Checks (exit non-zero on any failure):
#   GET /api/health          — ok=true, agents_ready=6, agents_total=6
#   GET /api/aether/status   — gate, frame_coverage, memory present
#
# Usage:
#   bash scripts/t2-staging-smoke.sh
#   ADVOI_BASE_URL=https://advoi-staging.keyteller.com bash scripts/t2-staging-smoke.sh
#   bash scripts/t2-staging-smoke.sh --fixture-dir tests/fixtures/t2-smoke
#
# Env:
#   ADVOI_BASE_URL          default https://advoi-staging.keyteller.com
#   ADVOI_EXPECTED_AGENTS   default 6
#   ADVOI_CURL_RETRIES      default 5 (live mode only)
#   ADVOI_CURL_RETRY_SLEEP  default 3 seconds between retries
#
# Cron example (after deploy window):
#   */15 * * * * cd /opt/advoi && ADVOI_BASE_URL=https://advoi-staging.keyteller.com \
#     bash scripts/t2-staging-smoke.sh >> /var/log/advoi-t2-smoke.log 2>&1
set -euo pipefail

ROOT="${ADVOI_REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
BASE="${ADVOI_BASE_URL:-https://advoi-staging.keyteller.com}"
EXPECTED_AGENTS="${ADVOI_EXPECTED_AGENTS:-6}"
RETRIES="${ADVOI_CURL_RETRIES:-5}"
RETRY_SLEEP="${ADVOI_CURL_RETRY_SLEEP:-3}"
FIXTURE_DIR=""
VALIDATE="${ROOT}/scripts/t2_validate.py"

usage() {
  sed -n '2,22p' "$0" | sed 's/^# \{0,1\}//'
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --fixture-dir)
      FIXTURE_DIR="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      ;;
    *)
      echo "Unknown arg: $1" >&2
      exit 2
      ;;
  esac
done

if [[ ! -f "${VALIDATE}" ]]; then
  echo "FAIL: missing validator ${VALIDATE}" >&2
  exit 1
fi

FAIL=0

run_validate() {
  local kind="$1"
  local body="$2"
  if echo "${body}" | python3 "${VALIDATE}" "${kind}" --expected-agents "${EXPECTED_AGENTS}"; then
    return 0
  fi
  return 1
}

curl_json() {
  local url="$1"
  local attempt body code
  for attempt in $(seq 1 "${RETRIES}"); do
    body="$(curl -sfS --max-time 20 "${url}" 2>/dev/null)" && {
      echo "${body}"
      return 0
    }
    code="$(curl -sS -o /dev/null -w "%{http_code}" --max-time 20 "${url}" 2>/dev/null || echo "000")"
    echo "    attempt ${attempt}/${RETRIES} failed (http=${code})" >&2
    if [[ "${attempt}" -lt "${RETRIES}" ]]; then
      sleep "${RETRY_SLEEP}"
    fi
  done
  return 1
}

echo "==> T2 staging smoke"
if [[ -n "${FIXTURE_DIR}" ]]; then
  echo "    mode: fixture (${FIXTURE_DIR})"
else
  echo "    base: ${BASE}"
fi
echo "    expected agents: ${EXPECTED_AGENTS}"
echo ""

# --- /api/health ---
echo "==> GET /api/health"
if [[ -n "${FIXTURE_DIR}" ]]; then
  health_path="${FIXTURE_DIR}/health.json"
  if [[ ! -f "${health_path}" ]]; then
    echo "    FAIL: missing ${health_path}"
    FAIL=1
  else
    health_body="$(cat "${health_path}")"
    if run_validate health "${health_body}"; then
      echo "    OK"
    else
      echo "    body: ${health_body}"
      FAIL=1
    fi
  fi
else
  if health_body="$(curl_json "${BASE}/api/health")"; then
    if run_validate health "${health_body}"; then
      echo "    ${health_body}"
      echo "    OK"
    else
      echo "    body: ${health_body}"
      FAIL=1
    fi
  else
    echo "    FAIL: unreachable ${BASE}/api/health"
    FAIL=1
  fi
fi
echo ""

# --- /api/aether/status ---
echo "==> GET /api/aether/status"
if [[ -n "${FIXTURE_DIR}" ]]; then
  aether_path="${FIXTURE_DIR}/aether-status.json"
  if [[ ! -f "${aether_path}" ]]; then
    echo "    FAIL: missing ${aether_path}"
    FAIL=1
  else
    aether_body="$(cat "${aether_path}")"
    if run_validate aether "${aether_body}"; then
      echo "    OK"
    else
      echo "    body (truncated): ${aether_body:0:400}"
      FAIL=1
    fi
  fi
else
  if aether_body="$(curl_json "${BASE}/api/aether/status")"; then
    if run_validate aether "${aether_body}"; then
      echo "    OK"
    else
      echo "    body (truncated): ${aether_body:0:400}"
      FAIL=1
    fi
  else
    echo "    FAIL: unreachable ${BASE}/api/aether/status"
    FAIL=1
  fi
fi
echo ""

if [[ "${FAIL}" -eq 0 ]]; then
  echo "T2 staging smoke PASSED"
  exit 0
fi

echo "T2 staging smoke FAILED" >&2
exit 1
