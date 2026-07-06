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

## [Future Entry Placeholder]

**Version:** v0.3.0  
**Type:** Feature  
**Status:** Not started

### Planned: Stage 2 Decision Frames

- Decision Frame buttons wired to API
- FirstMate fleet bridge from voice intents
- Trigger word / wake phrase

---

*Add new entries above the "Future Entry Placeholder" section.*