# E2E voice sign-off (staging)

Human validation template for Path A (LiveKit + server TTS). Copy this section into `docs/dev-log/DEV-LOG.md` or a ticket when signing off.

**Environment (canonical staging):** `https://advoi-staging.keyteller.com`  
**Live (do not treat as tip staging):** `https://advoi.keyteller.com`  
**Deploy ref / date:** VPS tree `5d50805` / 2026-07-10 (bootstrap; develop tip `3d5a00d` **not** promoted — GAP-013)  
**Tester:** ____________________  
**Browser / device:** ____________________

## Automated clearance (2026-07-10 — fleet ops recheck)

These passed against **bootstrap** staging before human test. Re-run after every promote:

- [x] `t2-staging-smoke.sh` — health 6/6 + aether/status (exit 0) @ advoi-staging
- [x] `staging-signoff-precheck.sh` — exit 0 with `ADVOI_BASE_URL=https://advoi-staging.keyteller.com`
- [x] `/api/health` — 6/6 agents, `stage=voice-pwa-2`
- [ ] Latency SLA — still open (`sla_ok=false` ~1.2s API path; does not fail precheck today)
- [ ] **Tip parity** — blocked until GAP-013 promote lands develop on VPS

**Scope:** Green T2 proves bootstrap SHA `5d50805` only — not develop tip.

## Pre-checks (automated)

Always set the fleet staging host (script default is still live host):

```bash
ADVOI_BASE_URL=https://advoi-staging.keyteller.com bash scripts/staging-signoff-precheck.sh
# minimum post-deploy:
ADVOI_BASE_URL=https://advoi-staging.keyteller.com bash scripts/t2-staging-smoke.sh
```

**Windows:** use PowerShell only (WSL bash does not inherit `$env:ADVOI_BASE_URL`):

```powershell
$env:ADVOI_BASE_URL = "https://advoi-staging.keyteller.com"
.\scripts\staging-signoff-precheck.ps1
```

Or individually:

- [ ] `bash scripts/voice-smoke-test.sh` → `/api/diagnostics/voice` reports `"ok": true`
- [ ] `bash scripts/agents-smoke-test.sh` (or `.ps1`) → all 6 agents + 6 frames OK
- [ ] `GET /api/diagnostics/latency` → `sla_ok: true` (API path under 800ms)
- [ ] `docker compose --profile app ps` → `advoi-api`, `advoi-voice`, `advoi-web`, `livekit` up
- [ ] `grep -E '^(OPENAI_API_KEY|OPENROUTER_API_KEY)=' deploy/.env` → non-empty on VPS

## Path A — LiveKit voice (required)

1. Open https://advoi-staging.keyteller.com on phone or desktop Chrome.
2. Tap **Connect voice** and allow microphone access.

| Step | Action | Pass |
|------|--------|------|
| 3 | Hear ADVoi greeting within ~10s of connect | [ ] |
| 4 | Tap **Option A** (fleet) — hear spoken summary | [ ] |
| 5 | Tap **Option B** (briefs) — hear brief list or empty message | [ ] |
| 6 | Tap **Option C** (review) twice — confirm flow, hear queue message | [ ] |
| 7 | PWA shows no error state; connection indicator green | [ ] |

**Pass criteria:** Audio on steps 3–6; no crash or silent failure.

## Optional — Path B (client voice loop)

Not required for staging sign-off. Record only if tested.

- [ ] `/voice-local` loads Kokoro + Parakeet models (WebGPU browser)
- [ ] Speak short phrase → hear Kokoro TTS reply via `POST /api/voice/respond`

## Home briefs + review queue (A17)

- [ ] On `/`, `pwa-home-briefs-surface` shows **Open briefs** + **Review queue** without navigating to `/briefs`
- [ ] Open briefs cards from thin `GET /api/briefs` (or empty state); **Hear open briefs** runs the `open_briefs` frame
- [ ] Pending review items appear under **Review queue** (`GET /api/review-queue`); cards link to `brief_url` or `/briefs/{id}`
- [ ] Voice/tap confirm on Option C (`queue_deep_review`) updates the home review list (post-frame `advoi:briefs-refresh`)

## Sign-off

| Field | Value |
|-------|-------|
| Overall result | [ ] **PASS** / [ ] **FAIL** |
| Date | |
| Notes / blockers | |

## On failure

1. `docker compose --profile app logs advoi-voice --tail 80`
2. `bash scripts/repair-vps-env.sh` (VPS) — fixes merged `.env` lines and refreshes Traefik labels
3. `bash scripts/sync-llm-keys-from-clapart.sh && bash scripts/ensure-deploy-secrets.sh`
4. `docker compose --profile app up -d --force-recreate advoi-voice`

See [staging-runbook.md](staging-runbook.md) for full recovery steps.