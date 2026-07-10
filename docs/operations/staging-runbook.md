# Staging runbook

VPS: `deploy@187.77.140.216`.

**Canonical staging (www tier):** path `/var/www/advoi/staging`, public https://advoi-staging.keyteller.com  
**Live:** `/var/www/advoi/live` → https://advoi.keyteller.com  
**Develop:** `/data/projects/advoi` (branch `develop`, tip `3d5a00d` as of ops review)  
**Legacy (deprecating):** `/opt/advoi` — old single-path stack until cutover; do not treat as the only staging location.

### Current drift (2026-07-10)

| Tier | Ref | Note |
|------|-----|------|
| Develop | `3d5a00d` | paperclip ingest + later data/arch ships |
| Staging VPS | `5d50805` | **behind** develop |
| Promote | **parked** | GAP-013 — SSH host key verification failed |
| T2 smoke | **pass** @ URL | Proves bootstrap `5d50805` only — not tip parity |

Fleet snapshot: `/data/staging-state.md`. Gap register: [gaps-and-blockers.md](../current-state/gaps-and-blockers.md) · [ROADMAP-VALIDATION.md](ROADMAP-VALIDATION.md) GAP-013.

Full path model: [docs/VPS-SETUP.md](../VPS-SETUP.md).

## Pre-deploy checklist

- [ ] `deploy/.env` not corrupt (`grep PROJECT_SLUG=advoi deploy/.env`)
- [ ] `OPENAI_API_KEY` or `OPENROUTER_API_KEY` set (non-empty)
- [ ] `HINDSIGHT_BRIDGE_URL=http://advoi-memory-bridge:8095`
- [ ] `ADVOI_SHELVE_PULL` unset or `false`
- [ ] OTel (moat R6): `OTEL_ENABLED=true` and `OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317` (gRPC). Staging redeploy starts collector via `--profile observability`. **VPS apply may be SSH-parked** — verify with `GET /api/diagnostics/platform` → `otel_ready: true` when host is reachable.

## Deploy

### Preferred — promote to www staging

```bash
# After changes land on develop checkout (/data/projects/advoi):
bash /var/www/advoi/promote-to-staging.sh
curl https://advoi-staging.keyteller.com/api/health
ADVOI_BASE_URL=https://advoi-staging.keyteller.com bash scripts/t2-staging-smoke.sh
```

Host script `promote-to-staging.sh` is not in this repo (no `scripts/www/` yet).

**Blocked (GAP-013):** SSH host key verification failed — do not assume a green T2 means tip is live. Unblock `known_hosts` / host key, then promote and re-smoke.

### Legacy — compose on `/opt/advoi`

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

## Postgres migrations (API boot)

Versioned SQL lives in `deploy/migrations/` and is applied **idempotently on `advoi-api` boot** via `advoi.db.migrations.apply_pending_migrations` (tracked in `schema_migrations`).

| Order | File |
|------:|------|
| 0 | `000_baseline_tables.sql` (`memory_events`, `decision_briefs`, `review_queue`) |
| 1 | `001_portfolio_events.sql` (PEL + backfill) |
| 2 | `002_review_queue_status_idx.sql` (pending FIFO index) |

Full runbook (local apply, staging verification, recovery): **[MIGRATIONS.md](MIGRATIONS.md)**.

**VPS-direct SSH apply is parked** for this ship — land on `develop`, promote, then verify `schema_migrations` rows after API restart (see MIGRATIONS.md § Staging verification).

## Post-deploy smoke

### T2 minimum (required after every app deploy)

Canonical job: **`scripts/t2-staging-smoke.sh`** — curls `/api/health` (expects `agents_ready=6` and `agents_total=6`) and `/api/aether/status` (gate + frame_coverage + memory). **Exits non-zero on failure.**

```bash
# Default base is https://advoi-staging.keyteller.com
bash scripts/t2-staging-smoke.sh

# Production-facing staging host (legacy STOREFRONT_HOST)
ADVOI_BASE_URL=https://advoi.keyteller.com bash scripts/t2-staging-smoke.sh
```

`scripts/staging-redeploy.sh` runs this automatically at the end of deploy.

Offline / CI unit path (fixtures, no network):

```bash
bash scripts/t2-staging-smoke.sh --fixture-dir tests/fixtures/t2-smoke
uv run pytest tests/test_t2_staging_smoke.py -q
```

Cron (optional VPS watch):

```cron
*/15 * * * * cd /opt/advoi && ADVOI_BASE_URL=https://advoi-staging.keyteller.com \
  bash scripts/t2-staging-smoke.sh >> /var/log/advoi-t2-smoke.log 2>&1
```

### Extended smoke

```bash
curl https://advoi-staging.keyteller.com/api/health
ADVOI_BASE_URL=https://advoi-staging.keyteller.com bash scripts/voice-smoke-test.sh
ADVOI_BASE_URL=https://advoi-staging.keyteller.com bash scripts/agents-smoke-test.sh
bash scripts/memory-health.sh
# Full pre-human sign-off (explicit host — script default is live):
ADVOI_BASE_URL=https://advoi-staging.keyteller.com bash scripts/staging-signoff-precheck.sh
```

Expected (bootstrap `5d50805` re-verified 2026-07-10):

- `/api/health` → `"stage": "voice-pwa-2"`, `agents_ready=6`, `agents_total=6`
- `/api/aether/status` → 200 with `gate`, `frame_coverage`, `memory.letta_health`
- `/api/diagnostics/voice` → `"ok": true` when keys set
- All three frame POSTs return `spoken_summary`
- `POST /api/voice/respond` → JSON with `spoken` (requires LLM keys)
- `GET /api/frames` → each frame has `voice_prompt` (intent catalog)
- `/api/agents` → six agents with `last_run` after warmup
- Precheck may still report `sla_ok=false` (~1.2s) while exit 0 — record latency separately

## Human E2E checklist (5 minutes)

Path A (staging default):

1. Open https://advoi-staging.keyteller.com on phone or desktop Chrome
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