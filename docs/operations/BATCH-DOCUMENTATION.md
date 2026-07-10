# Batch documentation discipline

**Purpose:** Gate new fleet dispatch until a work batch is fully documented. Prevents context loss across multi-agent sprints.  
**Baseline:** 2026-07-10, repo `advoi-system`  
**Related:** [DEV-LOG.md](../dev-log/DEV-LOG.md) | [DECISION-LOG.md](../decision-log/DECISION-LOG.md) | [OPPORTUNITIES-LOG.md](../opportunities-log/OPPORTUNITIES-LOG.md) | [ALIGNMENT-LOG.md](../alignment-log/ALIGNMENT-LOG.md) | [ROADMAP-VALIDATION.md](ROADMAP-VALIDATION.md)

---

## When to stop dispatch

**STOP** starting new Queued fleet tasks when **any** trigger fires:

| Trigger | Rule |
|---------|------|
| **Volume** | **5** backlog items moved to **Done** in the current batch |
| **Milestone** | A roadmap milestone (M1–M9) is marked complete or ready for sign-off |
| **Blockers** | **2+** items are **Parked** with unresolved blockers |

When triggered:

1. Do **not** dispatch new Queued tasks from FirstMate / fm-bridge / squad bridge.
2. Finish in-flight work only (no new scope).
3. Run the wrap-up procedure below before resuming dispatch.

Human E2E (M2) does **not** block development — but deferrals and parked blockers **do** count toward the blocker trigger. Track human tests in [MANUAL-TEST-TRACKER.md](MANUAL-TEST-TRACKER.md).

---

## Mandatory wrap-up artifacts

Every batch wrap-up must produce **all** of the following before Queued dispatch resumes.

| Artifact | Location | Minimum content |
|----------|----------|-----------------|
| **DEV-LOG** | [docs/dev-log/DEV-LOG.md](../dev-log/DEV-LOG.md) | New dated entry: summary, changes checklist, commits, next steps |
| **DECISION-LOG** | [docs/decision-log/DECISION-LOG.md](../decision-log/DECISION-LOG.md) | New ADR if any architectural or process decision was made |
| **OPPORTUNITIES-LOG** | [docs/opportunities-log/OPPORTUNITIES-LOG.md](../opportunities-log/OPPORTUNITIES-LOG.md) | Deferred work, follow-ups, and improvement ideas surfaced during the batch |
| **ALIGNMENT-LOG** | [docs/alignment-log/ALIGNMENT-LOG.md](../alignment-log/ALIGNMENT-LOG.md) | How batch outcomes align with roadmap milestones and fleet discipline |
| **Evidence folder** | `data/feedback-evidence/batch-YYYY-MM-DD/` | Screenshots, curl transcripts, pytest output, staging smoke logs |

### Evidence folder layout

```
data/feedback-evidence/batch-2026-07-10/
├── README.md              # What this batch proved; links to commits
├── pytest-summary.txt     # uv run pytest -q output
├── staging-smoke/         # Optional T2 curls / signoff precheck
└── screenshots/           # Optional PWA / dashboard captures
```

Create the folder even for docs-only batches (use `README.md` + note "docs-only, T0 skipped").

---

## Wrap-up procedure (step-by-step)

### 1. Freeze dispatch

- [ ] Confirm a stop trigger fired (5 Done / milestone / 2+ parked blockers).
- [ ] Notify fleet: no new Queued dispatch until wrap-up complete.
- [ ] Let in-flight tasks finish; do not pull new scope.

### 2. Collect evidence

- [ ] Run `uv run pytest tests/ -q` — save output to evidence folder.
- [ ] If code reached staging: run T2 smoke per [ROADMAP-VALIDATION.md](ROADMAP-VALIDATION.md) appendix; save transcripts.
- [ ] Attach relevant screenshots or API responses.

### 3. Update logs

- [ ] **DEV-LOG** — prepend dated entry with version, type, status, summary, changes, commits, next.
- [ ] **DECISION-LOG** — add ADR if a significant choice was made (see ADR template in that file).
- [ ] **OPPORTUNITIES-LOG** — record deferred milestones, infra follow-ups, and improvement ideas.
- [ ] **ALIGNMENT-LOG** — one entry tying batch outcomes to M1–M9 cadence and fleet rules.

### 4. Cross-check roadmap

- [ ] Update milestone status in [ROADMAP-VALIDATION.md](ROADMAP-VALIDATION.md) or [DEVELOPMENT-MILESTONES.md](../current-state/DEVELOPMENT-MILESTONES.md) if tasks closed.
- [ ] Update [SYSTEM-STATUS.md](../current-state/SYSTEM-STATUS.md) if build posture changed.
- [ ] Parked blockers reflected in [gaps-and-blockers.md](../current-state/gaps-and-blockers.md).

### 5. Commit and push

- [ ] Single docs commit (or docs + evidence) on a `fm/*` branch.
- [ ] PR title: `docs: batch wrap-up YYYY-MM-DD` with checklist in body.

### 6. Resume Queued dispatch

- [ ] All mandatory artifacts present and linked.
- [ ] Evidence folder committed or attached to PR.
- [ ] Explicit **resume** message to fleet / FirstMate bridge.
- [ ] Next Queued item may dispatch.

---

## Quick reference

```
Trigger? → STOP new dispatch → evidence → DEV/DECISION/OPPORTUNITY/ALIGNMENT logs → commit → resume Queued
```

| Question | Answer |
|----------|--------|
| Docs-only batch? | Still update DEV-LOG + ALIGNMENT-LOG; evidence README notes T0 skipped |
| Fewer than 5 Done? | No volume trigger; continue unless milestone or 2+ parked blockers |
| Who owns wrap-up? | Batch captain / last dispatcher before STOP |
| ADR required every batch? | Only when a significant decision was made; process ADR-027 covers the gate itself |

---

*See ADR-027 (Batch documentation wrap-up gate) in [DECISION-LOG.md](../decision-log/DECISION-LOG.md).*