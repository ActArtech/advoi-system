#!/usr/bin/env bash
# Test a branch on staging before merge.
# Usage: bash /var/www/advoi/checkout-pr.sh <branch-name>
set -euo pipefail

BRANCH="${1:?usage: checkout-pr.sh <branch-name>}"
bash "$(dirname "$0")/deploy-staging.sh" "$BRANCH"