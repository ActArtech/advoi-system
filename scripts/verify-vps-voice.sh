#!/usr/bin/env bash
set -euo pipefail

echo "==> containers"
docker ps --format '{{.Names}}' | grep advoi

echo "==> api key in voice"
docker exec advoi-advoi-voice-1 python -c '
import os
k = os.getenv("OPENAI_API_KEY", "")
print("len", len(k), "bad", k.endswith("true"))
'

echo "==> tts test"
docker exec advoi-advoi-voice-1 python -c '
import os
from openai import OpenAI
c = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
r = c.audio.speech.create(model="tts-1", voice="alloy", input="ok")
print("tts_bytes", len(r.content))
'

echo "==> fleet data visible in api container"
docker exec advoi-advoi-api-1 test -f /opt/firstmate-fleet/data/backlog.md
docker exec advoi-advoi-api-1 test -f /opt/firstmate-fleet/state/.afk

echo "==> fleet frame (fresh, bypass cache)"
FLEET_JSON="$(curl -sf -X POST 'https://advoi.keyteller.com/api/frames/fleet_status/run?refresh=true' -H 'Content-Type: application/json' -d '{"refresh":true}')"
echo "${FLEET_JSON}" | head -c 500
echo
if echo "${FLEET_JSON}" | grep -qi 'container firstmate-fleet not running'; then
  echo "FAIL: fleet frame still using docker-exec error"
  exit 1
fi
if ! echo "${FLEET_JSON}" | grep -qi 'fleet snapshot'; then
  echo "FAIL: fleet frame missing file-based snapshot"
  exit 1
fi
echo "OK: fleet frame returned file-based status"