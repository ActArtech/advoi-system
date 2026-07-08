# E2E voice sign-off (staging)

Human validation template for Path A (LiveKit + server TTS). Copy this section into `docs/dev-log/DEV-LOG.md` or a ticket when signing off.

**Environment:** `https://advoi.keyteller.com`  
**Deploy ref / date:** ____________________  
**Tester:** ____________________  
**Browser / device:** ____________________

## Pre-checks (automated)

- [ ] `bash scripts/voice-smoke-test.sh` → `/api/diagnostics/voice` reports `"ok": true`
- [ ] `bash scripts/agents-smoke-test.sh` (or `.ps1`) → all 3 agents + 3 frames OK
- [ ] `docker compose --profile app ps` → `advoi-api`, `advoi-voice`, `advoi-web`, `livekit` up
- [ ] `grep -E '^(OPENAI_API_KEY|OPENROUTER_API_KEY)=' deploy/.env` → non-empty on VPS

## Path A — LiveKit voice (required)

1. Open https://advoi.keyteller.com on phone or desktop Chrome.
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

## Review queue UI

- [ ] PWA shows **Review queue (N)** when items pending (`GET /api/review-queue`)
- [ ] Voice confirm on Option C updates queue list

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