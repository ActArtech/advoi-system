# Staging runbook

VPS: `deploy@187.77.140.216`, path `/opt/advoi`, public `https://advoi.keyteller.com`.

## Pre-deploy checklist

- [ ] `deploy/.env` not corrupt (`grep PROJECT_SLUG=advoi deploy/.env`)
- [ ] `OPENAI_API_KEY` or `OPENROUTER_API_KEY` set (non-empty)
- [ ] `HINDSIGHT_BRIDGE_URL=http://advoi-memory-bridge:8095`
- [ ] `ADVOI_SHELVE_PULL` unset or `false`

## Deploy

```bash
cd /opt/advoi
git pull origin master
cp deploy/.env.staging.example deploy/.env   # only if missing
sed -i 's/change-me-advoi-pg/advoi/' deploy/.env
bash scripts/sync-llm-keys-from-clapart.sh
bash scripts/ensure-deploy-secrets.sh
bash scripts/seed-advoi-briefs.sh
DEPLOY_MODE=staging bash scripts/vps-deploy.sh --profile app
```

Force voice recreate after key fix:

```bash
docker compose --profile app up -d --force-recreate advoi-voice
```

## Post-deploy smoke

```bash
bash scripts/voice-smoke-test.sh
# Or:
ADVOI_BASE_URL=https://advoi.keyteller.com bash scripts/agents-smoke-test.sh
bash scripts/memory-health.sh
```

Expected:

- `/api/health` → `"stage": "voice-pwa-2"`
- `/api/diagnostics/voice` → `"ok": true` when keys set
- All three frame POSTs return `spoken_summary`
- `POST /api/voice/respond` → JSON with `spoken` (requires LLM keys)
- `GET /api/frames` → each frame has `voice_prompt` (intent catalog)
- `/api/agents` → three agents with `last_run` after ~45s

## Human E2E checklist (5 minutes)

Path A (staging default):

1. Open https://advoi.keyteller.com on phone or desktop Chrome
2. **Connect voice** — allow mic
3. Hear ADVoi greeting within ~10s
4. Tap **Option A** (fleet) — hear spoken summary
5. Tap **Option B** (briefs) — hear brief list or empty message
6. Tap **Option C** (review) twice — confirm flow, hear queue message

Pass criteria: audio on steps 3-6, no error state on PWA.

Optional Path B (local client loop, not staging-validated):

1. Open `/voice-local` on a WebGPU-capable browser
2. Wait for Kokoro + Parakeet model load
3. Tap listen, speak a short question, hear Kokoro TTS reply

Sign-off:

- [ ] Path A human E2E passed (date, tester, browser/device)
- [ ] Record result in `docs/dev-log/DEV-LOG.md` or ticket

## Recovery: no voice

```bash
docker compose --profile app ps advoi-voice
docker compose --profile app logs advoi-voice --tail 80
grep OPENAI_API_KEY deploy/.env
```

If key empty:

```bash
bash scripts/sync-llm-keys-from-clapart.sh
bash scripts/ensure-deploy-secrets.sh
docker compose --profile app up -d --force-recreate advoi-voice
```

## Recovery: API 404

Usually corrupt `.env` / Traefik labels:

```bash
cp deploy/.env.staging.example deploy/.env
bash scripts/ensure-deploy-secrets.sh
bash scripts/sync-llm-keys-from-clapart.sh
DEPLOY_MODE=staging bash scripts/vps-deploy.sh --profile app
```

## Agent logs

```bash
docker compose logs -f advoi-agent-fleet advoi-agent-briefs advoi-agent-review
```

Look for `tick ok: ok` every `ADVOI_AGENT_INTERVAL_SECS`.