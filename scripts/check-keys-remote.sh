#!/usr/bin/env bash
for f in /opt/advoi/deploy/.env /opt/clapart/deploy/.env; do
  echo "== $f"
  grep -E '^OPENAI_API_KEY=|^OPENROUTER_API_KEY=' "$f" | while IFS= read -r line; do
    key="${line%%=*}"
    val="${line#*=}"
    echo "$key len=${#val} endswith_true=$([[ "$val" == *true ]] && echo yes || echo no)"
  done
done