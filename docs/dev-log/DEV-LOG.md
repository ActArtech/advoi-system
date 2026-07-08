# ADVoi Development Log

> Chronological record of development activity, milestones, and implementation notes.  
> One entry per significant work session or release.

---

## How to Use This Log

### Entry Template

```markdown
## [YYYY-MM-DD] — Title

**Version:** vX.Y.Z  
**Author:** [name/agent]  
**Type:** Scaffold | Feature | Fix | Refactor | Docs | Infra  
**Status:** Complete | In Progress | Blocked

### Summary
[1-3 sentences: what was done and why]

### Changes
- [ ] Change 1
- [ ] Change 2

### Decisions Made
- [Link to ADR-XXX if applicable]

### Next Steps
- [ ] Item 1
- [ ] Item 2

### Notes
[Optional: blockers, learnings, deviations from plan]
```

### Versioning Convention

| Bump | When |
|------|------|
| **Major (X.0.0)** | Breaking architecture change, new vertical/agent |
| **Minor (0.X.0)** | New feature, new horizontal engine, new protocol |
| **Patch (0.0.X)** | Bug fix, doc update, config tweak |

---

## Log Entries

---

## [2026-07-08] — Docs and smoke tests aligned to landed features

**Version:** v0.2.1-docs  
**Author:** Docs session  
**Type:** Docs  
**Status:** Complete

### Summary

Updated current-state, voice-path architecture, staging runbook, and smoke scripts to match code already in repo: `plain_copy`, colon frame labels, `/api/voice/respond`, `voice-interface/` + `/voice-local`, and 69 passing tests. P0 blockers unchanged (VPS keys, human E2E sign-off).

### Changes

- [x] `docs/current-state/gaps-and-blockers.md` — resolved copy/respond/cache items; Path B partial
- [x] `docs/current-state/what-we-have.md` — voice-interface, respond API, 69 tests
- [x] `docs/architecture/02-voice-paths.md` — Path B partially landed
- [x] `scripts/voice-smoke-test.sh` — voice respond + frame intent checks
- [x] `scripts/agents-smoke-test.ps1` — same checks + `last_run` warn
- [x] `docs/operations/staging-runbook.md` — API expectations + E2E sign-off checkbox

### Notes

Intent routing (utterance → frame) remains catalog-only via `voice_prompt`; classifier not implemented.

---

## [2026-07-08] — Architecture and current-state documentation

**Version:** v0.2.0-docs  
**Author:** Docs session  
**Type:** Docs  
**Status:** Complete

### Summary

Added structured documentation tree: architecture (5 docs), current-state (gaps, roadmap, inventory), operations (local + staging runbooks). Updated docs hub and root README. Marked `PLAN-SETUP-REVIEW.md` partially superseded.

### Changes

- [x] `docs/architecture/` — overview, voice paths, multi-agent, memory, deployment
- [x] `docs/current-state/` — what-we-have, gaps-and-blockers, improvement-roadmap
- [x] `docs/operations/` — local-testing, staging-runbook
- [x] `docs/README.md` — master index
- [x] Root `README.md` — links to new hub

### Notes

Reflects Stage 1.5 (3 agents, frames, memory bridge). Client Kokoro path documented as planned, not in repo.

---

## [2026-07-07] — Hermes cost optimization directive

**Version:** v0.1.3  
**Author:** Docs session  
**Type:** Docs  
**Status:** Complete

### Summary

Added portfolio-wide Hermes Cost Optimization Directive (5 priority sections) and ADVoi-specific cost notes for Hindsight/voice coexistence.

### Changes

- [x] `deployment/hermes/HERMES-COST-OPTIMIZATION.md` — canonical directive
- [x] `docs/HERMES-COST-OPTIMIZATION.md` — ADVoi operator context
- [x] Linked from `MEMORY-STACK.md`, `PLAN-SETUP-REVIEW.md`, Hermes ops docs

---

## [2026-07-07] — Plan setup review & insight documentation

**Version:** v0.1.2  
**Author:** Review session  
**Type:** Docs  
**Status:** Complete

### Summary

Documented Stage 1 plan setup gaps (deploy blockers, Shelve, portfolio registration) and distilled all eight conversation `.txt` sources into `docs/insights/` markdown files.

### Changes

- [x] `docs/PLAN-SETUP-REVIEW.md` — exit criteria, blockers, priority actions
- [x] `docs/insights/01`–`08` — voice, Pipecat, ontology, data/BI, agentic loops, AI-native SaaS, memory, poker/venture
- [x] `docs/insights/README.md` — index + architecture mapping
- [x] Updated `docs/README.md`, `SOURCE-MATERIALS.md`, `VERSIONS.md`

### Key findings

- Code ~75% for Stage 1; success signal blocked by API port/env bugs and missing secrets
- HTTPS `advoi.keyteller.com` returns 404 — app profile not healthy
- Shelve `ktteam/advoi/staging` not fully wired

### Next Steps

- [ ] Fix API port semantics and compose `env_file`
- [ ] Create Shelve project + deploy app profile
- [ ] E2E voice test; update portfolio inventory

---

## [2026-07-07] — VPS Clone + Infra (clone-only policy)

**Version:** v0.1.1  
**Author:** Setup session  
**Type:** Infra  
**Status:** Complete

### Summary

Cloned `advoi-system` to `/opt/advoi` on VPS without touching `/opt/firstmate`, `/opt/firstmate-fleet`, `/opt/aether`, or any other project. Started isolated postgres + redis; verified read-only fleet bridge.

### Changes

- [x] Clone-safe scripts: `vps-bootstrap.sh`, `vps-deploy.sh`, `vps-staging-check.sh`
- [x] GitHub deploy key `github-advoi` (read-only)
- [x] VPS clone at `/opt/advoi` — fresh, not migrated/overwritten
- [x] Docker project `advoi`: postgres `127.0.0.1:5438`, redis `127.0.0.1:6382`
- [x] `fm-bridge.sh` → `firstmate-fleet` fleet status verified
- [x] `docs/VPS-SETUP.md` + Traefik staging overlay (not deployed yet)

### Decisions Made

- **Clone-only:** refuse bootstrap if `/opt/advoi` exists without `.git`
- **No active venture switch:** gem-dev-shop remains Aether active project

### Next Steps

- [ ] DNS `advoi.keyteller.com` A record
- [ ] LiveKit credentials in `deploy/.env`
- [ ] Stage 1 voice agent + web PWA
- [ ] Register slug in `/opt/shared/port-registry.md`
- [ ] Bootstrap `.aether/` on advoi repo (optional, non-destructive)

---

## [2026-07-07] — Initial Scaffold & Documentation Capture

**Version:** v0.1.0  
**Author:** Architecture session (conversation capture)  
**Type:** Scaffold | Docs  
**Status:** Complete

### Summary

Created the `advoi-system` documentation scaffold to capture the full conversation evolution from exploratory discussions through locked architectural decisions. No application code deployed yet — this release establishes the clarity framework, decision log, dev log, and error log as the governance foundation for all subsequent implementation.

### Changes

- [x] Created `advoi-system/docs/` directory structure
- [x] Created `CLARITY-FRAMEWORK.md` — master clarity document
  - System vision (voice-first executive OS)
  - Strategy Stack ontology layers
  - Architecture layers (verticals + horizontals)
  - Evolution timeline (proposed → refined → rejected → final)
  - 24 locked final decisions
  - Version history (v0.1.0)
  - Open questions / deferred items
  - Tool/repo evaluation matrix (40+ tools evaluated)
- [x] Created `decision-log/DECISION-LOG.md` — 25 ADR-style decisions
- [x] Created `dev-log/DEV-LOG.md` — this file (template + first entry)
- [x] Created `error-log/ERROR-LOG.md` — Guardian agent error log template

### Source Material Captured

| File | Key Content Integrated |
|------|------------------------|
| `main1.txt` | Voice system, squads, Aether, Guardian, memory, decisions |
| `main2.txt` | Pipecat/LiveKit, FirstMate, React Flow, PWA, meta-architecture |
| `ontology.txt` | Strategy Stack, events, JTBD, harness mapping |
| `data.txt` | Ingestion, warehouse, BI, Coolify rejection |
| `aganticall.txt` | Agentic loops, progressive discovery |
| `newaistanderd.txt` | AI-Native SaaS principles |
| `gstak tenet.txt` | Memory system comparisons |

### Architecture Locked (Not Yet Built)

| Layer | Status |
|-------|--------|
| Web PWA client | 📋 Specified |
| LiveKit + Pipecat voice pipeline | 📋 Specified |
| Intent & Routing (local LLM) | 📋 Specified |
| Aether (portfolio manager) | 📋 Specified |
| Guardian (security/recovery) | 📋 Specified |
| Squad experiments (5-role + 3-role) | 📋 Specified |
| Ingestion Engine (horizontal) | 📋 Specified |
| Reporting Engine (horizontal) | 📋 Specified |
| PostgreSQL warehouse | 📋 Specified |
| React Flow architecture viz | 📋 Specified |
| Hermes + FirstMate integration | ✅ Existing (unchanged) |

### Decisions Made

- ADR-001 through ADR-025 documented in decision log
- See `CLARITY-FRAMEWORK.md` Section 5 for quick reference

### Next Steps

- [ ] Stage 1 implementation: Pipecat + LiveKit voice pipeline on VPS
- [ ] Web PWA shell with LiveKit web client integration
- [ ] Thin voice wrapper → FirstMate webhook/bot connection
- [ ] PostgreSQL schema-per-project initial migration
- [ ] `master-state.json` / per-project `.ether` schema design
- [ ] Guardian error log integration (wire to monitoring)
- [ ] React Flow SystemNode prototype for architecture dashboard
- [ ] OpenRouter tiered routing config for testing
- [ ] Backblaze B2 backup automation script

### Notes

- Conversation initially explored APK/React Native — **final decision is Web PWA first** (ADR-001)
- Lavish and Coolify explicitly rejected — do not re-introduce without new ADR
- Two squad experiments run in parallel — not a 5→3 reduction
- Financial agent (P&L) is future scope, separate from Aether
- Continuous Improvement Loop, DEL triggers, and dashboard UI are deferred but documented

---

## v0.2.0 — Stage 1 Voice + PWA

**Date:** 2026-07-07  
**Type:** Feature  
**Status:** Landed (deploy pending LiveKit creds)

### Shipped

- Pipecat agent (`advoi-voice`) — LiveKit transport, OpenAI STT/LLM/TTS
- FastAPI (`advoi-api`) — `/health`, `/api/livekit/token`, `/api/session`
- Next.js PWA (`web/`) — LiveKit client, connect/disconnect, manifest
- Scripts: `run-stage1-setup.sh`, `port-registry-apply.sh`, `aether-bootstrap.sh`
- `.aether/` bootstrap — BET, STAGE, EVENTS, PRINCIPLES/VOICE
- VPS port registry row applied at `/opt/shared/port-registry.md`

### Next

- Set `LIVEKIT_*` + `OPENAI_API_KEY` in `deploy/.env`
- `DEPLOY_MODE=staging bash scripts/vps-deploy.sh --profile app`
- Decision Frame button actions (Stage 2)

---

## v0.3.0 — Stage 1.5 Multi-agent + Intent

**Date:** 2026-07-08
**Type:** Feature
**Status:** Complete (code); staging automated clearance done

### Shipped

- Keyword intent routing (`advoi/routing/intent.py`) + `/api/voice/intent`
- LiveKit `VoiceIntentProcessor` — spoken "fleet status" routes to frames
- Review queue Postgres (`advoi/memory/review_queue.py`) + `GET /api/review-queue`
- Client voice loop (`/voice-local`) with Kokoro/Parakeet + intent preview
- PWA agent freshness chips, confirmation flow in VoiceLoop
- Voice diagnostics LLM key fail-fast; smoke tests expanded
- PowerShell startup scripts: `start-api.ps1`, `start-supervisor.ps1`, `start-web.ps1`
- **107 pytest tests**; CI: python + web + agents-smoke + staging-smoke

### Next

- Human phone E2E — `docs/operations/E2E-SIGNOFF.md`
- Port registry row to vps-shared

---

## [2026-07-08] — Build 1.5 automated staging clearance

**Version:** v0.3.1  
**Type:** Infra  
**Status:** Complete (automated); human E2E pending

### Summary

Staging at `advoi.keyteller.com` passes all automated gates. Build 1.5 is code-complete; only human mic → TTS sign-off blocks "validated" status.

### Automated proof (staging)

- `voice-smoke-test.sh` — all checks, `sla_ok: true`, ~35ms API path
- `/api/health` — 3/3 agents ready
- `/api/diagnostics/voice` — ok, llm_key, memory_bridge hermes
- Traefik env repaired; `ADVOI_SHELVE_PULL=false`; LLM keys from clapart
- PWA `/` + `/briefs/[id]` — 200
- Latency baseline: `docs/operations/latency-baseline.json`

### Still open (human)

- [ ] Phone: connect voice, hear greeting + frame TTS — E2E-SIGNOFF.md
- [ ] Optional: "queue review" → "yes" on device
- [ ] Port registry sync to vps-shared

### Reference

- `docs/current-state/BUILD-1.5-FINAL.md`

---

## [2026-07-08] — Build 1.5 finalized (automated gates)

**Version:** v0.3.1  
**Type:** Docs  
**Status:** Complete (automated); human E2E pending

### Summary

Gap table reviewed and closed for everything an agent can verify. `staging-signoff-precheck.ps1` passed at commit `c14c38d`. Build 1.5 is frozen until human phone sign-off.

### Gap table final

| Priority | Item | Result |
|----------|------|--------|
| P0 | Human E2E voice | **OPEN** — user on phone |
| P0 | LLM keys / Shelve | **DONE** |
| P1 | Two-turn confirm | **BUILT** — device test optional |
| P1 | Path B WebGPU | **BUILT** — not device-tested |
| P1 | Latency < 800ms | **PARTIAL** — API ok; voice round-trip TBD |
| P2 | Letta, OTel, Aether, dashboard | **Phase 4** — after sign-off |

### Next (human, ~15 min)

1. Open https://advoi.keyteller.com on phone
2. Connect voice, tap A/B/C, hear TTS
3. Record PASS in `docs/operations/E2E-SIGNOFF.md`
4. Then Phase 4 or port registry sync

---

## [Future Entry Placeholder]

**Version:** v0.4.0  
**Type:** Feature  
**Status:** Not started

### Planned: Stage 2 Decision Frames

- Decision Frame buttons wired to API
- FirstMate fleet bridge from voice intents
- Trigger word / wake phrase

---

*Add new entries above the "Future Entry Placeholder" section.*