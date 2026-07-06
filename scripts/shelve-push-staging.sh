#!/usr/bin/env bash
# One-time / refresh: push ADVoi staging secrets to Shelve (team ktteam / project advoi).
# Merges deploy/.env.staging.example + VPS /opt/advoi/deploy/.env + clapart OPENAI from Shelve.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

VPS_HOST="${VPS_HOST:-deploy@187.77.140.216}"
CLAPART_ENV_REMOTE="${CLAPART_ENV_REMOTE:-/opt/clapart/clapart-main/clapart-main/deploy/.env}"
ADVOI_ENV_REMOTE="${ADVOI_ENV_REMOTE:-/opt/advoi/deploy/.env}"
OUT="${ROOT}/deploy/.env"
EXAMPLE="${ROOT}/deploy/.env.staging.example"

if [[ ! -f "${EXAMPLE}" ]]; then
  echo "ERROR: missing ${EXAMPLE}" >&2
  exit 1
fi

if ! command -v npx >/dev/null 2>&1; then
  echo "ERROR: npx required (npm install --save-dev @shelve/cli from repo root)" >&2
  exit 1
fi

cp "${EXAMPLE}" "${OUT}"

_merge_key() {
  local key="$1" value="$2"
  [[ -z "${value}" ]] && return 0
  if grep -q "^${key}=" "${OUT}"; then
    sed -i "s|^${key}=.*|${key}=${value}|" "${OUT}"
  else
    echo "${key}=${value}" >> "${OUT}"
  fi
}

_read_remote() {
  local file="$1" key="$2"
  ssh -o ConnectTimeout=15 -o BatchMode=yes "${VPS_HOST}" \
    "grep -m1 '^${key}=' '${file}' 2>/dev/null | cut -d= -f2-" || true
}

echo "==> Merging VPS advoi deploy/.env (non-empty keys only)"
while IFS= read -r line; do
  [[ "${line}" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]] || continue
  key="${line%%=*}"
  val="${line#*=}"
  [[ -n "${val}" ]] && _merge_key "${key}" "${val}"
done < <(ssh -o ConnectTimeout=15 -o BatchMode=yes "${VPS_HOST}" "cat '${ADVOI_ENV_REMOTE}' 2>/dev/null" || true)

echo "==> Overlay clapart OPENAI / OPENROUTER / DEEPGRAM (if set on VPS)"
for key in OPENAI_API_KEY OPENROUTER_API_KEY DEEPGRAM_API_KEY OPENAI_FRAMEWORK_MODEL; do
  val="$(_read_remote "${CLAPART_ENV_REMOTE}" "${key}")"
  if [[ -n "${val}" ]]; then
    _merge_key "${key}" "${val}"
    echo "    ${key} ← clapart"
  fi
done

# Shelve rejects empty values — strip blanks and comments
grep -E '^[A-Za-z_][A-Za-z0-9_]*=.' "${OUT}" > "${OUT}.tmp"
mv "${OUT}.tmp" "${OUT}"
chmod 600 "${OUT}"

key_count=$(grep -cE '^[A-Za-z_][A-Za-z0-9_]*=' "${OUT}" || true)
echo "==> Pushing ${key_count} keys to Shelve (advoi / staging)"
npx --yes @shelve/cli --non-interactive --yes push --env staging

echo "==> Done. On VPS: shelve pull then redeploy:"
echo "    cd /opt/advoi && source /opt/shelve/scripts/shelve-pull-deploy.sh && shelve_pull_deploy /opt/advoi"
echo "    DEPLOY_MODE=staging bash scripts/vps-deploy.sh --profile app advoi-voice"