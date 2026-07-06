#!/usr/bin/env bash
# Bootstrap .aether/ on advoi repo only — does not touch /opt/aether or other ventures.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AETHER_DIR="${ROOT}/.aether"

echo "==> Aether bootstrap (advoi repo only)"

required=(
  README.md BET.md STAGE.md EVENTS.md DECISIONS.md VERSION
  PRINCIPLES/VOICE.md
)

missing=0
for f in "${required[@]}"; do
  if [[ ! -f "${AETHER_DIR}/${f}" ]]; then
    echo "MISSING: .aether/${f}"
    missing=1
  fi
done

if [[ "${missing}" -eq 1 ]]; then
  echo "ERROR: run from a complete advoi-system checkout" >&2
  exit 1
fi

echo "OK: .aether present with ${#required[@]} required artifacts"
echo "    Active venture remains gem-dev-shop until explicit promotion"
echo "    Decisions: docs/decision-log + .aether/DECISIONS.md"