#!/usr/bin/env bash
# ADVoi fleet feed cron — honor FM_AETHER_GATE_REQUIRED before publish.
#
# When FM_AETHER_GATE_REQUIRED=1 (default for this entrypoint), run
# fm-aether-gate first and **skip feed publish** if gate exit >= 2 (FAIL).
# Exit 0 (PASS) and 1 (PASS_AUDIT_ONLY) allow feed to proceed.
#
# Usage:
#   bash scripts/aether-feed-cron.sh
#   FM_ACTIVE_PROJECT=advoi FM_AETHER_GATE_REQUIRED=1 bash scripts/aether-feed-cron.sh
#
# Cron example (fleet host, after proactive cycle):
#   15 */4 * * * FM_ACTIVE_PROJECT=advoi FM_AETHER_GATE_REQUIRED=1 \
#     bash /data/projects/advoi/scripts/aether-feed-cron.sh \
#     >> /var/log/advoi-aether-feed.log 2>&1
#
# Test hooks (do not set in production):
#   FM_AETHER_GATE_CMD   — override gate command (e.g. "exit 2")
#   FM_AETHER_FEED_CMD   — override feed command (e.g. "echo FEED_RAN")
#   FM_AETHER_GATE_EXIT  — if set, skip real gate and use this exit code
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# This cron entrypoint defaults to required. Callers may set 0 to bypass.
export FM_AETHER_GATE_REQUIRED="${FM_AETHER_GATE_REQUIRED:-1}"
export FM_ACTIVE_PROJECT="${FM_ACTIVE_PROJECT:-advoi}"
export FM_AETHER_PROJECT_ROOT="${FM_AETHER_PROJECT_ROOT:-${ROOT}}"

GATE_SCRIPT="${FM_AETHER_GATE_SCRIPT:-/opt/firstmate/scripts/fm-aether-gate.sh}"
FEED_SCRIPT="${FM_AETHER_FEED_SCRIPT:-/opt/firstmate/scripts/fm-aether-feed.sh}"
GATE_CMD="${FM_AETHER_GATE_CMD:-}"
FEED_CMD="${FM_AETHER_FEED_CMD:-}"

log() {
  echo "$@"
}

run_gate() {
  # Always capture non-zero under set +e so `return $rc` is safe with set -e
  # callers (bash exits on failing return when -e is active inside the function).
  local rc=0
  if [[ -n "${FM_AETHER_GATE_EXIT:-}" ]]; then
    rc="${FM_AETHER_GATE_EXIT}"
    log "GATE_EXIT=${rc} (mocked via FM_AETHER_GATE_EXIT)"
  elif [[ -n "${GATE_CMD}" ]]; then
    set +e
    bash -c "${GATE_CMD}"
    rc=$?
    set -e
  elif [[ ! -f "${GATE_SCRIPT}" ]]; then
    log "WARN: gate script missing (${GATE_SCRIPT}) — treating as FAIL (exit 2)"
    rc=2
  else
    set +e
    bash "${GATE_SCRIPT}"
    rc=$?
    set -e
  fi
  # Propagate via stdout marker is avoided; caller uses set +e around invoke.
  # Disable -e for the return so non-zero does not abort the script mid-function.
  set +e
  return "${rc}"
}

run_feed() {
  if [[ -n "${FEED_CMD}" ]]; then
    bash -c "${FEED_CMD}"
    return $?
  fi
  if [[ ! -f "${FEED_SCRIPT}" ]]; then
    log "ERROR: feed script missing (${FEED_SCRIPT})" >&2
    return 1
  fi
  bash "${FEED_SCRIPT}"
}

gate_rc=0
if [[ "${FM_AETHER_GATE_REQUIRED}" == "1" ]]; then
  log "==> aether-feed-cron gate check (FM_AETHER_GATE_REQUIRED=1)"
  set +e
  run_gate
  gate_rc=$?
  set -e
  if [[ "${gate_rc}" -ge 2 ]]; then
    # Canonical skip line — asserted by tests/test_aether_feed_cron.py
    log "aether-feed: skipped — gate FAIL (exit=${gate_rc}) [FM_AETHER_GATE_REQUIRED=1]"
    exit 0
  fi
  if [[ "${gate_rc}" -eq 1 ]]; then
    log "==> gate PASS_AUDIT_ONLY (exit=1) — proceeding to feed"
  else
    log "==> gate PASS (exit=${gate_rc}) — proceeding to feed"
  fi
else
  log "==> aether-feed-cron gate not required (FM_AETHER_GATE_REQUIRED=${FM_AETHER_GATE_REQUIRED})"
fi

log "==> aether-feed-cron publish"
run_feed
log "==> aether-feed-cron done"
