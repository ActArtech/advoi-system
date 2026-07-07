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

echo "==> docker from api"
docker exec advoi-advoi-api-1 docker ps --format "{{.Names}}" | grep firstmate-fleet || echo "fleet not visible"

echo "==> fleet frame"
curl -sf -X POST https://advoi.keyteller.com/api/frames/fleet_status/run -H "Content-Type: application/json" -d "{}" | head -c 300
echo