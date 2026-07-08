# Build 1.5 — Final status

**Date:** 2026-07-08  
**Commit:** `65780eb` (GitHub `ActArtech/advoi-system`)  
**Staging:** https://advoi.keyteller.com

This document answers: *have we done the gap table items, and what is next?*

---

## Gap table — done vs open

| Priority | Gap | Status | Evidence |
|----------|-----|--------|----------|
| **P0** | Human E2E voice sign-off | **OPEN — you** | Automated gates pass; mic → TTS not recorded. Use [E2E-SIGNOFF.md](../operations/E2E-SIGNOFF.md) |
| **P0** | LLM keys / Shelve corruption | **DONE (mitigated)** | `ADVOI_SHELVE_PULL=false`; `ensure-deploy-secrets.sh` + clapart key sync; `repair-vps-env.sh` |
| **P1** | LiveKit two-turn confirm | **BUILT — device test open** | `intent_processor.py` + unit tests; say "queue review" → "yes" on phone |
| **P1** | Path B iOS WebGPU | **BUILT — validation open** | `/voice-local` + WebGPU banner; desktop Chrome spot-check optional |
| **P1** | Latency under 800ms | **PARTIAL** | API path `sla_ok: true` (~35ms); baseline in [latency-baseline.json](../operations/latency-baseline.json); full voice round-trip needs human |
| **P2** | Letta, OTel, Aether, dashboard | **NOT STARTED** | Phase 4 after human sign-off |

---

## What is fully done (automated proof)

| Item | Proof |
|------|-------|
| 107 pytest | `uv run pytest tests/ -q` |
| Voice smoke (staging) | `ADVOI_BASE_URL=https://advoi.keyteller.com bash scripts/voice-smoke-test.sh` |
| Staging precheck | `bash scripts/staging-signoff-precheck.sh` |
| CI | `python` + `web` + `agents-smoke` + `staging-smoke` (on master push) |
| Traefik + env | `PROJECT_SLUG=advoi`, `STOREFRONT_HOST=advoi.keyteller.com` |
| 3 agents cached | `/api/agents` → 3/3 ready |
| Voice container | Pipecat connected, LLM key present |
| PWA | `/` 200, health strip, 3 frames, review queue |
| Briefs desktop | `/briefs/[id]` + `GET /api/review-queue/{id}` |

---

## Build 1.5 exit criteria (`.aether/STAGE.md`)

| Criterion | Status |
|-----------|--------|
| Voice + PWA + 3 agents + frames | **Done** |
| Intent routing + review queue | **Done** |
| Staging infra + Traefik | **Done** |
| Automated tests + CI | **Done** |
| Human E2E sign-off | **Waiting on you** |
| Port registry → vps-shared | **Open** (copy row from `deploy/port-registry-entry.md`) |

---

## What you do next (15 minutes)

### 1. Run precheck (should pass)

```powershell
cd D:\Down\livekit-agent\deployment\advoi\advoi-system
.\scripts\staging-signoff-precheck.ps1
```

### 2. Phone test (closes P0)

1. Open https://advoi.keyteller.com
2. **Connect voice** — hear greeting within ~10s
3. Tap **Option A, B, C** — hear TTS each time
4. Optional: say **"queue review"** then **"yes"**
5. Fill [E2E-SIGNOFF.md](../operations/E2E-SIGNOFF.md) → Overall **PASS**

### 3. After PASS

- Add entry to `docs/dev-log/DEV-LOG.md`
- Mark human E2E box in `.aether/STAGE.md`
- Optional: sync port registry row to vps-shared repo
- **Then** start Phase 4 (Letta, OTel, dashboard)

---

## What we do not claim yet

- Production-validated voice (no human sign-off on file)
- iOS Path B WebGPU tested
- Real mic-STT-TTS latency measured end-to-end
- Letta / Guardian / Aether / React Flow dashboard

---

## Quick recovery if voice silent

```bash
ssh deploy@187.77.140.216
cd /opt/advoi
ADVOI_SHELVE_PULL=false DEPLOY_MODE=staging bash scripts/repair-vps-env.sh
bash scripts/sync-llm-keys-from-clapart.sh
docker compose -f docker-compose.yml -f deploy/docker-compose.staging.yml \
  --env-file deploy/.env --profile app up -d --force-recreate advoi-voice
```