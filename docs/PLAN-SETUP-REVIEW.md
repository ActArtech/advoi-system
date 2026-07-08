# ADVoi Plan Setup Review

> **⚠️ Historical document — do not use for current status**
>
> **Authoritative docs:** [current-state/](current-state/README.md) (gaps, roadmap, what we have), [architecture/](architecture/README.md), [operations/staging-runbook.md](operations/staging-runbook.md).
>
> This file is a 2026-07-07 onboarding snapshot. Many blockers listed below are mitigated or resolved; see [gaps-and-blockers.md](current-state/gaps-and-blockers.md).

**Date:** 2026-07-07  
**Stage:** Build 1.1 — Voice + PWA  
**Review method:** Parallel code + portfolio onboarding analysis against `NEW-PROJECT-DEPLOYMENT-GUIDE.md` and `.aether/STAGE.md`

---

## Executive summary

ADVoi has strong **planning and governance** (shaped bet, ADRs, `.aether/`) and **Stage 1 code is largely built** (voice agent, API, PWA scaffold, memory framework, deploy scripts). The **success signal is not met** because VPS app deployment is blocked by configuration bugs, secrets are not wired through Shelve, and end-to-end voice has not been validated.

| Layer | Status |
|-------|--------|
| Planning & governance | ✅ Strong |
| Stage 1 code | ~75% built |
| VPS infra (postgres/redis) | ✅ Running |
| VPS app stack (api/web/voice) | ❌ Blocked |
| Public HTTPS route | ❌ 404 |
| Portfolio registration | ⚠️ Partial |
| E2E voice validation | ❌ Not done |

---

## Success signal (from `.aether/STAGE.md`)

> User opens PWA, connects mic, hears ADVoi in LiveKit room; API health and token routes respond; port registry row present on VPS.

**Current verdict:** Not achievable until deploy blockers are fixed and LiveKit/OpenAI secrets are configured.

---

## Exit criteria checklist

| Criterion | Repo status | VPS / live status |
|-----------|-------------|-------------------|
| Pipecat + LiveKit voice agent | ✅ `advoi/voice/agent.py` | ❌ Container not healthy |
| Web PWA + LiveKit client | ✅ `web/components/VoiceSession.tsx` | ❌ Not deployed |
| API token endpoint | ✅ Tested (8/8 unit tests) | ❌ API unhealthy |
| `.aether/` bootstrap | ✅ Complete | N/A |
| Traefik at `advoi.keyteller.com` | ✅ Labels in staging compose | ❌ HTTPS 404 |
| Port registry on VPS | ✅ Script exists | ⚠️ VPS-local only; not in `vps-shared` |

---

## What's complete

### Code (Stage 1)

- **Voice** — Pipecat pipeline, LiveKit transport, memory recall at startup, greeting on first participant
- **API** — `/health`, `POST /api/livekit/token`, `GET /api/session`
- **Web** — Next.js PWA shell with mic connect flow
- **Memory** — `MemoryRouter`, Hindsight/Letta/Redis/Postgres scaffolding, setup scripts
- **Deploy** — `docker-compose.yml`, `deploy/docker-compose.staging.yml`, VPS scripts, Dockerfiles
- **Tests** — 8 passing (`test_api.py`, `test_memory.py`)

### VPS infra (partial)

Per `docs/dev-log/DEV-LOG.md` and `docs/PORTFOLIO-INTEGRATION.md`:

- Clone at `/opt/advoi` (clone-only policy respected)
- GitHub deploy key `github-advoi`
- Postgres `127.0.0.1:5438` + Redis `127.0.0.1:6382` healthy
- Port registry row on VPS `/opt/shared/port-registry.md`
- `fm-bridge.sh` fleet status verified read-only
- Hermes + firstmate-fleet + aether stacks untouched

### Portfolio onboarding (Phases A–G)

| Phase | Completion |
|-------|------------|
| A — Plan | ~90% |
| B — GitHub repo | ~70% |
| C — Shelve secrets | ~25% |
| D — VPS setup | ~80% |
| E — DNS + TLS | ~40% |
| F — Portfolio registration | ~25% |
| G — Aether bootstrap | ~90% |

---

## Critical gaps (blockers)

### 1. API port / healthcheck mismatch

`ADVOI_API_PORT` is used both as the **host bind** and the **container listen port**:

- `deploy/.env.staging.example` sets `ADVOI_API_PORT=8010`
- `advoi/api/main.py` listens on that value inside the container
- Healthcheck and Traefik expect port **8000**

**Fix:** Container always listens on 8000; use a separate variable (e.g. `ADVOI_API_HOST_PORT`) for host mapping `8010:8000`.

### 2. Compose `env_file` path

Services declare `env_file: .env` but secrets live in `deploy/.env`. The `--env-file` flag in `vps-deploy.sh` only affects compose interpolation, not per-service env injection.

**Fix:** Point compose at `deploy/.env` or symlink `.env` → `deploy/.env`.

### 3. Shelve not wired

`shelve.json` is missing `envFileName`, `autoCreateProject`, and `autoUppercase`. Shelve project `ktteam/advoi/staging` may not exist; pull fails. VPS `deploy/.env` is likely hand-copied.

**Required secrets still placeholder:**

- `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`
- `OPENAI_API_KEY`

### 4. App profile never reached healthy state

Observed VPS state (2026-07-07 review):

```
advoi-postgres-1    Up (healthy)
advoi-redis-1       Up (healthy)
advoi-advoi-api-1   Up (unhealthy)
advoi-advoi-web-1   Created (blocked on API health)
advoi-advoi-voice-1 Created (blocked on API health)
```

Traefik terminates TLS but returns **404** — no healthy backends registered.

### 5. No end-to-end voice test

No integration test for PWA → token → LiveKit → mic → spoken greeting. Unit tests cover API and memory routing only.

---

## Secondary gaps

| Gap | Impact |
|-----|--------|
| Not in `deployment/VPS-PROJECT-INVENTORY.md` | Portfolio visibility |
| Not in `ActArtech/vps-shared` port registry | Cross-project collision risk |
| No Paperclip project | Agent automation (optional) |
| Branch `master` vs guide `main` | Convention drift |
| `docker-compose.yml` at repo root | Deviates from standard template |
| `vps-deploy.sh` lacks Shelve pull | Day-2 secret workflow |
| PWA icons missing | Installable PWA incomplete |
| No service worker | Offline PWA incomplete |
| Memory `retain()` not in voice loop | Recall-only at startup |
| Traefik `/ws/voice` route | Dead for Stage 1 (voice is LiveKit client) |
| `docs/VERSIONS.md` / `DEV-LOG.md` stale | Operator confusion |
| Future verticals stubbed | Expected for Stage 1 |

---

## Architecture deferred (locked, not built)

From `CLARITY-FRAMEWORK.md` and conversation sources — see `docs/insights/`:

- Decision frames + briefs (Stage 2)
- Squad experiments (5-role + 3-role)
- React Flow architecture dashboard
- Ingestion + reporting engines
- PostgreSQL schema-per-project / `master-state.json`
- Guardian monitoring integration
- Letta operational memory (v0.2)
- SigNoz observability

---

## Priority action list

1. Fix API port semantics (container 8000, host 8010)
2. Fix `env_file` paths in compose
3. Create Shelve project `ktteam/advoi/staging` with all vars from `deploy/.env.staging.example`
4. Fill LiveKit + OpenAI secrets in Shelve
5. Update `shelve.json` with full template fields
6. Add Shelve pull to `vps-deploy.sh` (per deployment guide)
7. Deploy: `DEPLOY_MODE=staging bash scripts/vps-deploy.sh --profile app`
8. Smoke: `bash scripts/vps-staging-check.sh` → HTTP 200
9. Manual e2e: PWA → Connect voice → hear greeting
10. Register in `VPS-PROJECT-INVENTORY.md` + `vps-shared` port registry
11. Run `bash scripts/memory-health.sh` after Hindsight daemon warm

---

## 8-step VPS checklist status

From `docs/VPS-SETUP.md`:

| Step | Action | Status |
|------|--------|--------|
| 1 | Private GitHub repo | ✅ `ActArtech/advoi-system` |
| 2 | Deploy key `github-advoi` | ✅ Done |
| 3 | Clone to `/opt/advoi` | ✅ Done |
| 4 | Port registry row | ⚠️ VPS yes; `vps-shared` no |
| 5 | DNS A record | ✅ Wildcard covers host |
| 6 | `deploy/.env` + Shelve | ⚠️ File exists; Shelve not wired |
| 7 | Docker + Traefik labels | ⚠️ Infra only; app not healthy |
| 8 | Smoke HTTPS 200 | ❌ Returns 404 |

---

## Optimization (Hermes spend)

Before scaling voice + memory workloads, apply [HERMES-COST-OPTIMIZATION.md](HERMES-COST-OPTIMIZATION.md) (ADVoi notes) and the canonical [hermes/HERMES-COST-OPTIMIZATION.md](../../../hermes/HERMES-COST-OPTIMIZATION.md) on `/opt/hermes`. Priority: cheap auxiliary/sub-agent models, context compression, tool/MCP cleanup, `max_turns` + `hard_stop` on crons.

---

## Related docs

| Doc | Purpose |
|-----|---------|
| [VPS-SETUP.md](VPS-SETUP.md) | Deploy checklist |
| [HERMES-COST-OPTIMIZATION.md](HERMES-COST-OPTIMIZATION.md) | Hermes cost directive (ADVoi) |
| [PORTFOLIO-INTEGRATION.md](PORTFOLIO-INTEGRATION.md) | Fleet coexistence |
| [MEMORY-STACK.md](MEMORY-STACK.md) | Hindsight phases |
| [insights/README.md](insights/README.md) | Source conversation insights |
| [../deployment/NEW-PROJECT-DEPLOYMENT-GUIDE.md](../../NEW-PROJECT-DEPLOYMENT-GUIDE.md) | Portfolio standard |

---

*Next review trigger: after app profile deploy succeeds and e2e voice test passes.*