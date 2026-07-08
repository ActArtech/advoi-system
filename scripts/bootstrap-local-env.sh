#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="${ROOT}/deploy/.env.local.example"
DEST="${ROOT}/deploy/.env"
if [[ ! -f "${SRC}" ]]; then echo "ERROR: missing ${SRC}" >&2; exit 1; fi
if [[ -f "${DEST}" ]]; then echo "deploy/.env already exists"; exit 0; fi
cp "${SRC}" "${DEST}"
echo "OK: created deploy/.env"