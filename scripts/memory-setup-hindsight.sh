#!/usr/bin/env bash
# Configure Hermes + ADVoi for Hindsight strategic memory (ADR-026).
# Clone-safe: only writes Hermes /opt/data config — does not touch /opt/hermes repo.
set -euo pipefail

HERMES_CONTAINER="${HERMES_CONTAINER:-hermes}"
HERMES_DATA="${HERMES_DATA:-/opt/hermes/data}"
MODE="${HINDSIGHT_MODE:-local}"
BANK_ID="${HINDSIGHT_BANK_ID:-advoi-portfolio}"
LLM_PROVIDER="${HINDSIGHT_LLM_PROVIDER:-openai}"
LLM_MODEL="${HINDSIGHT_LLM_MODEL:-gpt-4o-mini}"

echo "==> Hindsight memory setup (mode=${MODE}, bank=${BANK_ID})"

if ! docker ps --format '{{.Names}}' | grep -qx "${HERMES_CONTAINER}"; then
  echo "ERROR: container '${HERMES_CONTAINER}' not running" >&2
  exit 1
fi

# Switch provider away from holographic (or other) → hindsight
docker exec "${HERMES_CONTAINER}" hermes config set memory.provider hindsight

mkdir -p "${HERMES_DATA}/hindsight"

cat > "${HERMES_DATA}/hindsight/config.json" <<EOF
{
  "mode": "${MODE}",
  "api_url": "https://api.hindsight.vectorize.io",
  "apiPort": 9077,
  "bank_id": "${BANK_ID}",
  "bankMission": "ADVoi executive portfolio memory — ventures, governance, cross-project synthesis.",
  "retainMission": "Extract durable portfolio facts, governance decisions, venture beliefs, and operational lessons worth recalling later.",
  "llm_provider": "${LLM_PROVIDER}",
  "llm_model": "${LLM_MODEL}",
  "autoRecall": true,
  "autoRetain": true,
  "memory_mode": "hybrid",
  "recallBudget": "mid",
  "daemonIdleTimeout": 0
}
EOF

# Secrets live in Hermes env file (never echo values)
HERMES_ENV="${HERMES_DATA}/.env"
touch "${HERMES_ENV}"

if [[ "${MODE}" == "cloud" ]]; then
  if [[ -z "${HINDSIGHT_API_KEY:-}" ]]; then
    echo "WARN: HINDSIGHT_MODE=cloud but HINDSIGHT_API_KEY not set in shell."
    echo "      Add HINDSIGHT_API_KEY=hs_... to ${HERMES_ENV} and re-run."
  else
    if grep -q '^HINDSIGHT_API_KEY=' "${HERMES_ENV}"; then
      sed -i "s|^HINDSIGHT_API_KEY=.*|HINDSIGHT_API_KEY=${HINDSIGHT_API_KEY}|" "${HERMES_ENV}"
    else
      echo "HINDSIGHT_API_KEY=${HINDSIGHT_API_KEY}" >> "${HERMES_ENV}"
    fi
  fi
else
  # Local embedded: reuse existing OPENAI_API_KEY from Hermes env when present
  if ! grep -q '^HINDSIGHT_LLM_API_KEY=' "${HERMES_ENV}"; then
    OPENAI_KEY="$(grep '^OPENAI_API_KEY=' "${HERMES_ENV}" | cut -d= -f2- || true)"
    if [[ -n "${OPENAI_KEY}" ]]; then
      echo "HINDSIGHT_LLM_API_KEY=${OPENAI_KEY}" >> "${HERMES_ENV}"
      echo "OK: wired HINDSIGHT_LLM_API_KEY from existing OPENAI_API_KEY"
    else
      echo "WARN: no OPENAI_API_KEY in ${HERMES_ENV}; add HINDSIGHT_LLM_API_KEY manually"
    fi
  fi
  grep -q '^HINDSIGHT_MODE=' "${HERMES_ENV}" \
    && sed -i 's|^HINDSIGHT_MODE=.*|HINDSIGHT_MODE=local|' "${HERMES_ENV}" \
    || echo "HINDSIGHT_MODE=local" >> "${HERMES_ENV}"
  grep -q '^HINDSIGHT_BANK_ID=' "${HERMES_ENV}" \
    && sed -i "s|^HINDSIGHT_BANK_ID=.*|HINDSIGHT_BANK_ID=${BANK_ID}|" "${HERMES_ENV}" \
    || echo "HINDSIGHT_BANK_ID=${BANK_ID}" >> "${HERMES_ENV}"
fi

# Install hindsight-client inside Hermes for bridge script
docker exec "${HERMES_CONTAINER}" uv pip install "hindsight-client>=0.6.1" >/dev/null 2>&1 || \
  docker exec "${HERMES_CONTAINER}" python -m pip install "hindsight-client>=0.6.1" >/dev/null 2>&1 || \
  echo "WARN: could not install hindsight-client in ${HERMES_CONTAINER} (bridge may fail until installed)"

echo "--- Hermes memory status ---"
docker exec "${HERMES_CONTAINER}" hermes memory status || true

ADVOI_ENV="${ADVOI_ENV_FILE:-/opt/advoi/deploy/.env}"
if [[ -f "${ADVOI_ENV}" ]]; then
  for kv in \
    "MEMORY_PROVIDER=hindsight" \
    "HINDSIGHT_MODE=${MODE}" \
    "HINDSIGHT_BRIDGE=hermes" \
    "HINDSIGHT_BANK_ID=${BANK_ID}" \
    "HERMES_CONTAINER=${HERMES_CONTAINER}" \
    "LETTA_ENABLED=false"; do
    key="${kv%%=*}"
    if grep -q "^${key}=" "${ADVOI_ENV}"; then
      sed -i "s|^${key}=.*|${kv}|" "${ADVOI_ENV}"
    else
      echo "${kv}" >> "${ADVOI_ENV}"
    fi
  done
  echo "OK: updated ${ADVOI_ENV}"
else
  echo "WARN: ${ADVOI_ENV} missing — copy deploy/.env.staging.example to deploy/.env"
fi

echo "==> Done. Warm Hindsight with one retain:"
echo "    docker exec ${HERMES_CONTAINER} python /vps-projects/advoi/scripts/hindsight-bridge.py --json '{\"action\":\"retain\",\"event_type\":\"portfolio_fact\",\"summary\":\"ADVoi memory stack online\",\"payload\":{\"project\":\"advoi\"}}'"