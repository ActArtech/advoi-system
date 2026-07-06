#!/usr/bin/env bash
# Optional Letta (Leda) operational memory — separate clone at /opt/letta (ADR-026 v0.2).
set -euo pipefail

LETTA_ROOT="${LETTA_ROOT:-/opt/letta}"
LETTA_PORT="${LETTA_PORT:-8283}"
LETTA_AGENT_ID="${LETTA_AGENT_ID:-advoi-executive}"
ADVOI_ENV="${ADVOI_ENV_FILE:-/opt/advoi/deploy/.env}"

echo "==> Letta memory setup (root=${LETTA_ROOT})"

if [[ -d "${LETTA_ROOT}" && ! -d "${LETTA_ROOT}/.git" ]]; then
  echo "ERROR: ${LETTA_ROOT} exists but is not a git directory — refusing to overwrite" >&2
  exit 1
fi

if [[ ! -d "${LETTA_ROOT}" ]]; then
  git clone https://github.com/letta-ai/letta.git "${LETTA_ROOT}"
fi

mkdir -p "${LETTA_ROOT}/data/pgdata" "${LETTA_ROOT}/data/memfs"

cat > "${LETTA_ROOT}/docker-compose.yml" <<EOF
name: letta

services:
  letta:
    image: letta/letta:latest
    restart: unless-stopped
    ports:
      - "127.0.0.1:${LETTA_PORT}:8283"
    environment:
      SECURE: "true"
      LETTA_SERVER_PASSWORD: \${LETTA_SERVER_PASSWORD:-change-me-letta}
      LETTA_MEMFS_SERVICE_URL: local
      OPENAI_API_KEY: \${OPENAI_API_KEY:-}
    volumes:
      - ./data/pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8283/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s

networks:
  default:
    name: letta-network
EOF

cat > "${LETTA_ROOT}/.env.example" <<'EOF'
LETTA_SERVER_PASSWORD=change-me-letta
OPENAI_API_KEY=
EOF

if [[ ! -f "${LETTA_ROOT}/.env" ]]; then
  cp "${LETTA_ROOT}/.env.example" "${LETTA_ROOT}/.env"
  echo "WARN: edit ${LETTA_ROOT}/.env with LETTA_SERVER_PASSWORD and OPENAI_API_KEY"
fi

cd "${LETTA_ROOT}"
docker compose --env-file .env up -d

echo "--- Letta health ---"
curl -sf "http://127.0.0.1:${LETTA_PORT}/v1/health" && echo " OK" || echo "WARN: health check pending (first boot can take ~60s)"

if [[ -f "${ADVOI_ENV}" ]]; then
  for kv in \
    "MEMORY_PROVIDER=both" \
    "LETTA_ENABLED=true" \
    "LETTA_BASE_URL=http://127.0.0.1:${LETTA_PORT}" \
    "LETTA_AGENT_ID=${LETTA_AGENT_ID}"; do
    key="${kv%%=*}"
    if grep -q "^${key}=" "${ADVOI_ENV}"; then
      sed -i "s|^${key}=.*|${kv}|" "${ADVOI_ENV}"
    else
      echo "${kv}" >> "${ADVOI_ENV}"
    fi
  done
  echo "OK: updated ${ADVOI_ENV}"
fi

echo "==> Create Letta agent '${LETTA_AGENT_ID}' via API after server is healthy."
echo "    See docs/LETTA-OPTIONAL.md for agent bootstrap with git-memory-enabled tag."