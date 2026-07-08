# Gaps and blockers

Issues that prevent calling ADVoi "production validated" today.

## P0 — Blocks staging voice

### 1. Voice container crash-loop (no audio)

**Status:** **Mitigated** when staging voice is healthy and LLM keys are present (verify with `voice-smoke-test.sh`).

**Symptom:** PWA connects (green), frame text appears, user hears nothing.

**Cause:** `advoi-voice` exits when `OPENAI_API_KEY` / `OPENROUTER_API_KEY` missing after `.env` restore from staging template.

**Error:** `RuntimeError: OPENROUTER_API_KEY or OPENAI_API_KEY is required for ADVoi voice`

**Fix:**

```bash
cd /opt/advoi
bash scripts/sync-llm-keys-from-clapart.sh
bash scripts/ensure-deploy-secrets.sh
docker compose --profile app up -d --force-recreate advoi-voice
bash scripts/voice-smoke-test.sh
```

### 2. Shelve corrupts `deploy/.env`

**Status:** **Mitigated** — pull disabled by default; root cause documented.

**Symptom:** Traefik 404, API unreachable, merged env lines (`LIVEKIT_API_SECRET=secretHINDSIGHT_BRIDGE_URL=...`).

**Root cause:** Shelve export and hand-edits produced lines without trailing newlines. The pre-fix `ensure-deploy-secrets.sh` merge regex (`(?<=[a-z0-9.])(?=[A-Z][A-Z0-9_]+=)`) could split valid keys (e.g. inside `PROJECT_SLUG`) and worsen corruption. Fixed regex now only splits merged `valueKEY=` boundaries; char-split files auto-restore from `.env.staging.example`.

**Mitigation shipped:** `ADVOI_SHELVE_PULL=false` by default; corrupt file auto-restore in `vps-deploy.sh`; `ensure-deploy-secrets.sh` + `repair-vps-env.sh` repair merged lines.

**Remaining gap:** Do not re-enable Shelve pull until token/format is validated end-to-end.

### 3. End-to-end voice not signed off

No recorded CI or human sign-off that mic → STT → LLM → TTS works on staging after last deploy. Use [E2E-SIGNOFF.md](../operations/E2E-SIGNOFF.md).

---

## P1 — Functional gaps

| Gap | Detail | Status |
|-----|--------|--------|
| Review queue UI | Postgres queue + `GET /api/review-queue`; PWA list in `VoiceSession.tsx` | **Resolved** |
| Intent confirm on LiveKit | Two-turn confirm wired in `intent_processor.py` (pending frame per session); needs staging device test | Open |
| Client voice path (Path B) | `voice-interface/`, `/voice-local`, Kokoro/Parakeet deps, and `POST /api/voice/respond` landed; browser model load and iOS WebGPU not validated on staging | Open |
| Memory bridge without Hermes | Local dev without Hermes: bridge returns errors (non-fatal for mock frames). `/api/diagnostics/voice` reports `memory_bridge_ok` and `memory_bridge_mode` (`hermes` \| `unavailable` \| `mock`) | **Mitigated** |

### Recently resolved (2026-07-08)

| Item | Status |
|------|--------|
| `plain_copy` / em dashes | `advoi/copy_style.py`; frame labels use `Option A:` colon format; spoken output normalized |
| `/api/voice/respond` | Implemented in `advoi/api/app.py`; used by `VoiceLoop` |
| `/api/voice/intent` | Keyword classify + optional frame preview; wired in `VoiceLoop` and `warm_spoken_reply` |
| Agent `last_run` cache | `advoi/cache/agent_cache.py` wired into `GET /api/agents` |
| Review queue persistence | `advoi/memory/review_queue.py` + desktop brief URL on confirm |
| LiveKit STT intent routing | `advoi/voice/intent_processor.py` in Pipecat pipeline |
| Voice diagnostics LLM check | `/api/diagnostics/voice` fails fast when keys missing |
| Review queue UI | `VoiceSession` review section lists pending items + brief links |
| LiveKit two-turn confirm | `intent_processor.py` pending frame per session; "queue review → yes" |
| Voice latency hints | `/api/diagnostics/voice` and `/api/diagnostics/latency` report `frame_run_ms` |
| Review queue PWA list | `VoiceSession.tsx` shows pending items from `/api/review-queue` |

---

## P2 — Platform / portfolio gaps

| Gap | Detail | Status |
|-----|--------|--------|
| Port registry in `vps-shared` | Row may exist on VPS only, not synced to shared repo | Open |
| DNS/TLS intermittently 404 | Traefik labels depend on valid `.env` `PROJECT_SLUG` and host rules | **Mitigated** via `scripts/repair-vps-env.sh` |
| Letta operational memory | Disabled; identity prefs not stored | Open |
| Observability | OTel collector profile exists; not wired into app traces | Open |
| Aether / Guardian / Squads | Package stubs only | Open |

---

## P3 — Quality and UX

| Gap | Detail |
|-----|--------|
| Agent interval 45s default | First `last_run` cache delay; acceptable for prod, slow for demos |
| No agent dashboard | No React Flow or status UI beyond PWA status line |
| iOS WebGPU / client voice | Path B scaffold present; not E2E tested on device |
| WSL vs Windows localhost | Bash smoke from WSL cannot hit Windows-bound API on `127.0.0.1:8010`; use `.ps1` |
| Stale governance docs | `PLAN-SETUP-REVIEW.md`, `.aether/STAGE.md` behind actual build |

---

## Blocker dependency graph

```mermaid
flowchart TD
  ENV[Valid deploy/.env]
  KEYS[LLM API keys]
  VOICE[advoi-voice healthy]
  LK[livekit reachable]
  E2E[E2E voice test]

  ENV --> KEYS
  KEYS --> VOICE
  ENV --> LK
  VOICE --> E2E
  LK --> E2E
```

## Definition of "ready for testing"

Minimum bar:

1. `deploy/.env` has LLM keys and LiveKit keys
2. `docker compose --profile app ps` shows api, voice, livekit, 3 agents up
3. `scripts/agents-smoke-test.ps1` passes
4. `scripts/voice-smoke-test.sh` passes against staging URL
5. Human: connect PWA, hear greeting, tap frame, hear spoken summary — record in [E2E-SIGNOFF.md](../operations/E2E-SIGNOFF.md)