# Batch documentation — First Mate mandatory wrap-up

**Audience:** First Mate captain + crew (AFK continuous loop)  
**Trigger:** After every **good batch** — defined below  
**Repo:** `ActArtech/advoi-system` develop tree `/data/projects/advoi`

A good batch is complete when **any** of:

- **5+** backlog items moved to `## Done` in one continuous loop wave
- A **milestone slice** ships (e.g. M1 staging, ADR-026 audit, PEL schema spike)
- **3+** related PRs merge or develop commits land with tests green
- Captain **parks 2+ blockers** and needs a decision/opportunity record before next wave

Do **not** skip wrap-up to start the next Queued item. Document first, then continue.

---

## Wrap-up checklist (all required)

| # | Artifact | Path | What to write |
|---|----------|------|---------------|
| 1 | **Dev log** | `docs/dev-log/DEV-LOG.md` | New dated entry: summary, changes, commits/SHAs, next steps |
| 2 | **Decision log** | `docs/decision-log/DECISION-LOG.md` | New ADR only if architectural/product choice was made; else "no new ADRs" line in dev log |
| 3 | **Opportunities** | `docs/current-state/OPPORTUNITIES-LOG.md` | Scout/harvest/implementation discoveries worth future work |
| 4 | **Alignment** | `docs/current-state/ALIGNMENT-LOG.md` | Gate, roadmap, moat, architecture doc alignment after batch |
| 5 | **Evidence** | `data/feedback-evidence/batch-YYYY-MM-DD/` (fleet) | `summary.md`, smoke logs, curl output, test results |
| 6 | **Backlog** | `/opt/firstmate-fleet/data/backlog.md` | Done section updated; parked items have `blocked-by:` |
| 7 | **Staging state** | `/opt/firstmate-fleet/data/staging-state.md` | SHA + smoke URL if staging touched |
| 8 | **Roadmap/moat** | `docs/operations/ROADMAP-VALIDATION.md` | Checkbox updates for milestones proven in batch |

Copy paths on develop: use `/data/projects/advoi/docs/...` inside fleet container.

---

## 1. Dev log entry template

```markdown
## [YYYY-MM-DD] — <batch title>

**Version:** v0.x.x (if bumped)  
**Type:** Feature | Docs | Infra | Fix  
**Status:** Complete | Partial | Blocked  
**Batch IDs:** advoi-xxx-01, advoi-yyy-02, ...

### Summary
<2-4 sentences: what shipped, what was proven on staging>

### Changes
- [x] <item>
- [ ] <parked — link blocked-by in fleet backlog>

### Evidence
- Staging: https://advoi-staging.keyteller.com/api/health @ `<sha>`
- Tests: `uv run pytest tests/ -q` → N passed
- Fleet evidence: `data/feedback-evidence/batch-YYYY-MM-DD/summary.md`

### Next
- <next Queued slice>
```

---

## 2. Decision log (when required)

Add **ADR-0XX** when the batch introduced or changed:

- Memory write targets or store authority
- Vertical boundaries or Guardian policy
- Data schema (PEL, ingestion lifecycle, ECR)
- Staging/live topology or fleet integration contract
- PWA interaction or analytics funnel definitions

If no decision: add to dev log: `**Decisions:** None — execution only.`

Use template in `DECISION-LOG.md` § ADR Template.

---

## 3. Opportunities log entry

```markdown
## [YYYY-MM-DD] — batch <title>

| ID | Opportunity | Lane | Value | Source | Notes |
|----|-------------|------|-------|--------|-------|
| OPP-NNN | <one line> | OPP/FEAT/ARCH | 1-10 | batch/implement/harvest | <why deferred> |
```

Promote value ≥7 + complexity ≤M to `data/harvest-backlog-advoi.md` or `data/feedback-backlog-advoi.md`.

**Harvest scouts (ADVoi):** use on-product lenses and report template in [HARVEST-RUBRIC-ADVOI.md](HARVEST-RUBRIC-ADVOI.md) (ingest lifecycle, voice/PWA, aether/PEL, fleet bridge, staging smoke, memory/ADR-026, ontology). Do not use agentsim-lab discovery targets. Fleet runtime copy is `/data/config/harvest-rubric.md` (FirstMate-owned merge).

---

## 4. Alignment log entry

```markdown
## [YYYY-MM-DD] — batch <title>

| Check | Status | Evidence |
|-------|--------|----------|
| Aether gate (`/api/aether/status`) | pass/hold/fail | verdict + active_slug |
| Fleet `active_slug` | advoi | fleet-profile.md |
| ROADMAP-VALIDATION milestones touched | M1.4, T2 smoke | curl log |
| PORTFOLIO-SYSTEM-MOAT R1-R10 | <which advanced> | moat review § |
| ARCHITECTURE-DATA-MEMORY-REVIEW | doc/code match | arch review § |
| Staging URL | advoi-staging.keyteller.com | health JSON |
| Drift: architecture docs | yes/no | 01-overview, 03-multi-agent |

**Misalignments found:** <list or "none">
**Follow-up backlog IDs:** <advoi-*>
```

---

## 5. Fleet evidence folder

On fleet host (or develop copy for PR):

```text
data/feedback-evidence/batch-2026-07-10/
  summary.md       # captain narrative
  done-items.txt   # ids moved to Done
  smoke.txt        # staging-signoff or curl output
  blockers.md      # parked with blocked-by
  opportunities.md # copy of OPP rows if not yet in repo
```

---

## 6. Promote to staging (if code changed)

```bash
bash /var/www/advoi/promote-to-staging.sh
ADVOI_BASE_URL=https://advoi-staging.keyteller.com bash scripts/staging-signoff-precheck.sh
```

Record SHA in dev log + ALIGNMENT-LOG + staging-state.md.

---

## Batch cadence in AFK loop

```text
Process Queued items → every 5 Done OR milestone complete:
  → run this checklist (do not skip)
  → fm-send captain: "Batch wrap-up complete. Resume Queued."
  → continue next item
```

Blocker during batch: still log partial wrap-up with `Status: Partial` and blockers.md.

---

## Changelog

| Date | Change |
|------|--------|
| 2026-07-10 | Link ADVoi harvest rubric ([HARVEST-RUBRIC-ADVOI.md](HARVEST-RUBRIC-ADVOI.md)) for scout/opportunity promote path |
| 2026-07-10 | Initial batch documentation standard for First Mate AFK loop |