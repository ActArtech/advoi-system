#!/usr/bin/env bash
# Generate GitHub deploy key for advoi-system (run once on VPS as deploy user).
# Does NOT modify keys for other repos.
set -euo pipefail

KEY_DIR="${HOME}/.ssh/repo-keys"
KEY_NAME=advoi-system
KEY_PATH="${KEY_DIR}/${KEY_NAME}"

mkdir -p "${KEY_DIR}"
chmod 700 "${KEY_DIR}"

if [[ -f "${KEY_PATH}" ]]; then
  echo "Deploy key already exists: ${KEY_PATH}"
else
  ssh-keygen -t ed25519 -f "${KEY_PATH}" -N "" -C "deploy@187.77.140.216 advoi-system"
  chmod 600 "${KEY_PATH}"
  chmod 644 "${KEY_PATH}.pub"
  echo "Created ${KEY_PATH}"
fi

SSH_CONFIG="${HOME}/.ssh/config"
if ! grep -q "Host github-advoi" "${SSH_CONFIG}" 2>/dev/null; then
  cat >> "${SSH_CONFIG}" <<EOF

Host github-advoi
  HostName github.com
  User git
  IdentityFile ${KEY_PATH}
  IdentitiesOnly yes
EOF
  chmod 600 "${SSH_CONFIG}"
  echo "Added Host github-advoi to ~/.ssh/config"
fi

echo ""
echo "Add this deploy key to GitHub → ActArtech/advoi-system → Settings → Deploy keys (read-only):"
echo "---"
cat "${KEY_PATH}.pub"
echo "---"
echo "Then run: bash scripts/vps-bootstrap.sh"