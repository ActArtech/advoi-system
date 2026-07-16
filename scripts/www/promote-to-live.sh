#!/usr/bin/env bash
# Promote staging -> live (no PR). Captain runs after staging smoke passes.
# Usage: bash /var/www/advoi/promote-to-live.sh
set -euo pipefail

WWW="/var/www/advoi"
STAGING="$WWW/staging"
SHA="$(git -C "$STAGING" rev-parse HEAD)"

echo "==> Promote staging @ $SHA -> live (master/main)"

cd "$WWW/live"
git fetch origin master main 2>/dev/null || git fetch origin
git checkout master 2>/dev/null || git checkout main
git merge --ff-only "$SHA" 2>/dev/null || git reset --hard "$SHA"

bash "$WWW/deploy-live.sh"

echo "==> Optional: push to GitHub when ready:"
echo "    cd $WWW/live && git push origin \$(git branch --show-current)"