#!/usr/bin/env bash
# Wrapper for memory_events age retention (safe default: dry-run).
#
# Usage:
#   bash scripts/memory-events-retention.sh              # dry-run
#   bash scripts/memory-events-retention.sh --dry-run
#   bash scripts/memory-events-retention.sh --apply
#   bash scripts/memory-events-retention.sh --apply --days 120
#
# Cron (weekly apply — only after dry-run has been verified):
#   20 3 * * 0 ENV_FILE=/opt/advoi/deploy/.env \
#     bash /opt/advoi/scripts/memory-events-retention.sh --apply \
#     >> /var/log/advoi-memory-events-retention.log 2>&1
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-${ROOT}/deploy/.env}"

if [[ -f "${ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
fi

export ENV_FILE

if command -v uv >/dev/null 2>&1; then
  exec uv run python "${ROOT}/scripts/memory-events-retention.py" "$@"
fi
exec python3 "${ROOT}/scripts/memory-events-retention.py" "$@"
