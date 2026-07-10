# Harvest scout rubrics — ADVoi

**Audience:** Harvest scouts (`harvest-scout-<lens>-*`) and FirstMate ingest (`harvest-ingest-report.sh`)  
**Product:** `advoi` (`ActArtech/advoi-system`)  
**Fleet config owner:** FirstMate merges this content into `/data/config/harvest-rubric.md` (see `data/harvest-advoi-rubric-01/firstmate-note.md`)  
**Related:** [BATCH-DOCUMENTATION.md](BATCH-DOCUMENTATION.md) · [staging-runbook.md](staging-runbook.md) · [MEMORY-STACK.md](../MEMORY-STACK.md) · [architecture/07-portfolio-event-log.md](../architecture/07-portfolio-event-log.md)

Use **one lens per scout**. Minimum **5** findings per report; rank by **value** (1–10). Prefer **on-product** discovery targets below — **do not** treat agentsim-lab (or other portfolio lab) URLs as primary walk targets.

---

## Primary discovery targets (ADVoi only)

| Surface | URL / path | Notes |
|---------|------------|--------|
| Staging PWA + API | https://advoi-staging.keyteller.com | Primary VAL/UX walk; T2 smoke baseline |
| Live (read-care) | https://advoi.keyteller.com | Compare drift only; no experimental writes |
| Product tree | `/data/projects/advoi` (or worktree root) | Source of truth for code + docs |
| Staging runbook | [staging-runbook.md](staging-runbook.md) | Deploy path, GAP-013 promote, T2 |
| Fleet snapshot | `/data/staging-state.md`, `/data/backlog.md` | SHA, Queued hygiene — not product code |
| Harvest backlog | `/data/harvest-backlog-advoi.md` | Ingest target for ship cards |

**Forbidden as primary discovery:** `https://agentsim-lab.keyteller.com`, agentsim assess/regression funnels, JMTS lab routes, `PLATFORM-GTM-ROADMAP` lab UX-NN items. Those belong to other fleet projects.

---

## Product lenses (preferred rotate set)

FirstMate should set `harvest-mode.md` `rotate_lenses` to these names when scouting ADVoi (custom lens → default lane **OPP** unless the report card sets `lane:` explicitly).

| Lens (spawn id) | Default lane | One-line focus |
|-----------------|--------------|----------------|
| `ingest-lifecycle` | FEAT | Upload → triage → review → approve → dispatch |
| `voice-pwa` | UX | LiveKit/Pipecat path + PWA frames/briefs/onboarding |
| `aether-pel` | ARCH | Aether gate feed + Portfolio Event Log emit/schema |
| `fleet-bridge` | ARCH | `fm-bridge` / Guardian / trigger idempotency |
| `staging-smoke` | VAL | T2 health, promote parity, signoff precheck |
| `memory-adr026` | ARCH | ADR-026 tiers: Hindsight / PG / Redis / optional Letta |
| `ontology` | ARCH | Registry + route/frame validators |

Standard fleet aliases (`validate`, `architecture`, `ux`, `refactor`, `feature`) remain below for spawn compatibility.

---

## ingest-lifecycle (FEAT)

**Code:** `advoi/ingestion/` · UI: `web/app/ingest/` · tests: `tests/test_ingestion*.py`

- Walk happy path **states only**: `uploaded → triaged → needs_review → approved → dispatched` (`lifecycle.py`). Invalid transitions → API **409**.
- Upload must stay **`uploaded`** (no silent auto-dispatch). Optional `auto_triage` only when explicit.
- API surface: `POST /api/ingestion/upload`, list/detail/summary, `…/triage`, `…/needs-review`, `…/approve`, `…/route`, `…/dispatch-dev` (dispatch **only** from `approved`).
- UI parity: triage / needs_review / approve controls vs dead `dispatch_dev` / auto-dispatch form fields.
- Parse allowlist (`.txt/.md/.json/.csv/.log/.yaml`), size limits (`ADVOI_INGEST_MAX_BYTES`).
- Routing: venture/keyword scores, `paperclip_ticket_id`, store under `ADVOI_INGESTION_PATH` (default `data/ingestion`).
- Gaps: classifier quality (`triage.py`), ontology venture reject (cross-lens `ontology`), filesystem vs future Postgres inbox.

---

## voice-pwa (UX)

**Code:** `web/components/VoiceSession.tsx`, `PwaHomeBriefsSurface.tsx`, `PwaHomeOnboarding.tsx` · `advoi/voice/` · [architecture/02-voice-paths.md](../architecture/02-voice-paths.md)

- Staging walk: home → install/onboarding CTA → connect voice → frame run → confirm/success (analytics funnel).
- Path A production: PWA → `POST /api/livekit/token` → LiveKit → Pipecat bot → TTS; frame path `POST /api/frames/{id}/run` + data-channel speak.
- Known failure: **connected green, no audio** when `advoi-voice` down — report as VAL/UX if unhandled in UI.
- Mobile **375px**: connect, latency chip, recovery, briefs empty/loading/error.
- Briefs surface: thin `GET /api/briefs` / review-queue; cache vs Postgres authority.
- Env: voice container needs `OPENAI_API_KEY` or `OPENROUTER_API_KEY`; crash-loop without keys is an ops finding, not a product experiment.

---

## aether-pel (ARCH)

**Code:** `advoi/aether/`, `advoi/analytics/pel.py`, `docs/aether/`, `scripts/aether-*.sh` · [architecture/07-portfolio-event-log.md](../architecture/07-portfolio-event-log.md)

- Gate feed: `docs/aether/aether-proactive-latest.json` + `AETHER-DIRECTIVES.md`; bootstrap `scripts/aether-bootstrap.sh`; `FM_ACTIVE_PROJECT=advoi bash /opt/firstmate/scripts/fm-aether-gate.sh`.
- Publish atomicity: `scripts/aether-publish-atomic.sh`; export: `scripts/aether-gate-export.sh` → repo `data/aether/aether-gate-latest.md` and/or PEL `source=aether`, `type=governance_decision`.
- PEL: append-only `portfolio_events` via `append_event`; emit points frame_run, fleet_trigger/guardian_gate, voice_intent, aether gate — not every Redis turn.
- Schema/migrations: `deploy/migrations/000_baseline_tables.sql`, `001_portfolio_events.sql`; boot apply `advoi.db.migrations`.
- Dual-authority risk: legacy `memory_events` vs PEL (must not invent a third write path).
- Staging proof: gate_snapshot rows, funnel SQL on PEL (see [ANALYTICS-FUNNEL.md](ANALYTICS-FUNNEL.md)).

---

## fleet-bridge (ARCH)

**Code:** `advoi/fleet/bridge.py`, `idempotency.py`, `trigger.py` · `scripts/fm-bridge.sh`

- Product dispatch path: ingestion `dispatch-dev` / Guardian confirmation → bridge → FirstMate trigger (`fm-hermes-trigger` family).
- Idempotency: double-dispatch, retry storms, `ADVOI_FLEET_MOCK` for T0.
- PEL emit on trigger/confirmation; `execution_ref` linkage to ingest item / job id.
- Separation of concerns: **product** inbox → fleet **work** is not the same as **harvest** scout → `harvest-backlog-advoi.md` → `backlog.md` cards.
- Discord/FirstMate ACK·PROMOTE·NEXT only as ops surface ([DISCORD-WORKFLOW.md](DISCORD-WORKFLOW.md)) — do not invent lab bot funnels.

---

## staging-smoke (VAL)

**Hosts:** https://advoi-staging.keyteller.com · scripts: `scripts/t2-staging-smoke.sh`, `scripts/staging-signoff-precheck.sh`, `scripts/voice-smoke-test.sh`

- T2 bootstrap health vs **tip parity** (develop SHA vs VPS SHA in `/data/staging-state.md`).
- Promote path: `scripts/www/promote-to-staging.sh` / host promote; GAP-013 SSH host key is a captain OPS item — scouts report, do not "fix" SSH from harvest.
- Checks: `GET /api/health`, diagnostics/platform (`otel_ready` when observability on), aether status when gate required.
- Evidence: save curl transcripts under `data/feedback-evidence/` for batch wrap-up — do not claim green T2 equals develop tip if SHA lags.
- Port/env drift: [PORT-REGISTRY.md](PORT-REGISTRY.md), `deploy/.env` keys (Hindsight bridge URL, LiveKit, DB).

---

## memory-adr026 (ARCH)

**Authority:** ADR-026 · [MEMORY-STACK.md](../MEMORY-STACK.md) · `advoi/memory/`

- Tiers: **Hindsight** (strategic, via memory-bridge :8095) · **Postgres** (canonical briefs + PEL) · **Redis** (ephemeral voice turns / briefs cache) · **Letta** optional v0.2.
- Write-target matrix: who may retain_structured, who may append PEL, who may touch Redis voice TTL.
- Compaction: Redis voice max turns + TTL; `memory_events` age prune (`scripts/memory-events-retention.sh`); **PEL is not age-pruned** by that job.
- Review queue / briefs triple-path: cache fill-on-read, invalidate-on-write, Postgres source of truth.
- Metrics/correlation: retain metrics, trace_id on PEL rows, fleet recall guards — look for dual-write or silent drop gaps.
- Never recommend docker.sock from app containers; only memory-bridge holds that.

---

## ontology (ARCH)

**Code:** `advoi/ontology/registry.py`, `validate.py` · ingest `route.py` · frame validators

- Registry is SoT for ventures/entities; route must not accept unregistered `venture_id` as success without flag/reject.
- Frame runner / post-frame hooks: ontology validation errors surface as 4xx/structured fail, not silent attach.
- Cross-check docs architecture vertical boundaries vs registry contents.
- Events/relationships: prefer named ontology types over ad-hoc JSON keys in PEL payloads.
- Tests: registry + frame validator coverage; fixtures under `tests/`.

---

## Standard spawn aliases (compatibility)

Keep these headings so `fm-spawn-harvest-scout.sh <lens>` still resolves when `rotate_lenses` uses the classic five.

### validate (VAL)

- Run `uv run pytest tests/ -q` (or focused `tests/test_ingestion*.py`, `tests/test_portfolio_events.py`, voice/memory tests) — note gaps, not full suite ownership.
- Staging: `bash scripts/t2-staging-smoke.sh` against https://advoi-staging.keyteller.com; compare SHA to develop tip.
- API contracts without tests: ingestion lifecycle transitions, PEL append idempotency, fleet bridge mock path.
- Env edge cases: missing LLM keys (voice crash-loop), `ADVOI_FLEET_MOCK`, `FM_AETHER_GATE_REQUIRED`.
- Prefer product checklist docs under `docs/operations/` and `docs/architecture/` over any lab health matrix.

### architecture (ARCH)

- Vertical boundaries: `advoi/{ingestion,voice,memory,ontology,fleet,aether,analytics,api}/` — no god imports across guardianship lines ([06-vertical-boundaries.md](../architecture/06-vertical-boundaries.md)).
- Dual-authority: `memory_events` vs `portfolio_events`; Redis cache vs Postgres briefs.
- God modules / orphan scripts; CI vs `scripts/*` drift.
- Aether gate export audit trail (git + PEL).
- Harvest plumbing only when it blocks ADVoi continuous improvement (project-aware cycle reports, rubric drift) — still **ADVoi** repo evidence.

### refactor (REF)

- Duplicated lifecycle/UI state strings between API and `web/app/ingest`.
- Repeated PWA empty/error patterns across home/voice/ingest.
- Test fixture duplication for frames, PEL rows, ingest items.
- Dead flags: auto-dispatch form fields, lab-only copy, unused env toggles.
- Complexity **L/XL** → recommend `split`, not a single ship card.

### ux (UX)

- Walk **https://advoi-staging.keyteller.com** (not lab): home, voice connect, briefs, ingest queue, onboarding.
- Mobile 375px: voice session, latency chip, recovery, confirm parity.
- Empty/loading/error for briefs and ingest list.
- Funnel: connect → frame → confirm → success ([ANALYTICS-FUNNEL.md](ANALYTICS-FUNNEL.md)).
- Accessibility / trust: connected-without-audio, failed dispatch messaging.

### feature (FEAT / OPP)

- Roadmap: [ROADMAP-VALIDATION.md](ROADMAP-VALIDATION.md) / milestones M1–M10 — next unshipped slice **≤M** complexity.
- Ingest classifier / ontology route reject / PEL read API / aether cron wire — only if not already Queued (check `/data/backlog.md` + `docs/current-state/OPPORTUNITIES-LOG.md`).
- Small wins: ingest UI lifecycle buttons, smoke evidence automation, PEL emit at missing source.
- Do **not** invent agentsim-style assess/export experiments.

---

## Report template (parser contract)

`harvest-ingest-report.sh` requires these section headings. Cards under **Top 3** (or Findings with value ≥6 when Top 3 empty) become harvest-backlog rows.

```markdown
# Harvest report — <lens> — <date>

## Executive summary (3 bullets)

- …
- …
- …

## Findings (table)
| ID | Lane | Value | Complexity | Evidence | Recommendation | Backlog action |
|----|------|-------|------------|----------|----------------|----------------|
| F1 | VAL | 8 | M | file:line or staging URL | Add tests / fix X | queue |
| F2 | ARCH | 5 | L | module boundary | Split god module | defer — split first |
| F3 | UX | 7 | S | staging screenshot / curl | Fix empty state | queue |

**Backlog action:** `queue` (value ≥6, complexity ≤M) · `defer` (L/XL or value <6) · `split` (XL epic → ≤3 PRs)

## Top 3 ship candidates (ready for backlog.md)
Use formal card format when possible (parser reads `lane:`, `value:`, `complexity:`, `gate:`):
1. harvest-<slug>-01 - <one line> (lane: VAL, repo: advoi, value: 8, complexity: M, gate: PR + T0 tests, promote: yes)
2. harvest-<slug>-02 - <one line> (lane: UX, repo: advoi, value: 7, complexity: S, gate: staging smoke, promote: yes)
3. harvest-<slug>-03 - <one line> (lane: ARCH, repo: advoi, value: 7, complexity: M, gate: PR + pytest, promote: yes)
```

### Parser notes

| Section | Ingest behavior |
|---------|-----------------|
| `## Executive summary` | Copied into harvest-backlog under Ingested summary |
| `## Findings (table)` | Value ≥6 → ship candidate if Top 3 empty; value &lt;6 or complexity L/XL → Deferred |
| `## Top 3 …` | Numbered or `-` lines become primary ship cards |
| Lanes | VAL · REF · ARCH · UX · OPP · FEAT (set explicitly on cards) |
| Complexity | S · M · L · XL — auto-dispatch bar is complexity ≤ **M** and value ≥ **6** (`harvest-mode.md`) |

---

## Anti-patterns

1. Primary UX walk on agentsim-lab or non-ADVoi portfolio doors.
2. Queuing work already Done / already in fleet `## Queued` without mapping note.
3. Treating product ingestion dispatch as harvest-card promote (different pipelines).
4. Claiming staging tip parity from bootstrap T2 alone when SHA lags develop.
5. Opening PRs from scout tasks — reports only; FirstMate ingest → promote → delegate.

---

*Baseline gap that motivated this doc: fleet `harvest-rubric.md` was agentsim-lab flavored while `harvest-mode.md` `target: advoi`. Repo copy lives here; fleet file is FirstMate-owned.*
