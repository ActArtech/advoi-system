#!/usr/bin/env bash
# Append advoi row to VPS port registry if missing (idempotent).
set -euo pipefail

REGISTRY="${PORT_REGISTRY_PATH:-/opt/shared/port-registry.md}"
ROW='| advoi | /opt/advoi | advoi.keyteller.com | PG 127.0.0.1:5438, Redis 127.0.0.1:6382, API 8010, Voice 8011, Web 3000 | Traefik advoi-web, advoi-api, advoi-voice; Shelve ktteam/advoi/staging |'

echo "==> Port registry apply (${REGISTRY})"

if [[ ! -f "${REGISTRY}" ]]; then
  mkdir -p "$(dirname "${REGISTRY}")"
  cat > "${REGISTRY}" <<'HDR'
# VPS Port Registry

| slug | path | host | ports | notes |
|------|------|------|-------|-------|
HDR
  echo "Created ${REGISTRY}"
fi

if grep -q '| advoi |' "${REGISTRY}"; then
  echo "OK: advoi row already present"
  grep '| advoi |' "${REGISTRY}"
  exit 0
fi

echo "${ROW}" >> "${REGISTRY}"
echo "OK: appended advoi row"
grep '| advoi |' "${REGISTRY}"