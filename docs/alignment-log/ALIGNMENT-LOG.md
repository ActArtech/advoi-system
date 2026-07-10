# ADVoi Alignment Log

> Records how fleet work batches align with roadmap milestones, validation tiers, and portfolio strategy.  
> Complements ADRs (decisions) and opportunities (deferrals) with explicit traceability.

---

## How to Use This Log

1. **Add an entry** at every batch wrap-up (see [BATCH-DOCUMENTATION.md](../operations/BATCH-DOCUMENTATION.md)).
2. **Reference milestones** M1–M9 and tiers T0–T3 from [ROADMAP-VALIDATION.md](../operations/ROADMAP-VALIDATION.md).
3. **Status values:** `Aligned` | `Partial` | `Drift` | `Corrected`
4. Cross-reference [PORTFOLIO-SYSTEM-MOAT.md](../reviews/PORTFOLIO-SYSTEM-MOAT.md) when batch work touches portfolio integration.

### Entry Template

```markdown
## ALN-YYYY-NNN: Short Title

**Date:** YYYY-MM-DD  
**Batch:** batch-YYYY-MM-DD  
**Status:** Aligned | Partial | Drift | Corrected

### Fleet batch summary
[What shipped or was parked in this batch]

### Roadmap alignment
| Milestone | Batch impact | Tier proof |
|-----------|--------------|------------|
| M# | ... | T# |

### Discipline checks
- [ ] Stop trigger honored before resume
- [ ] DEV / DECISION / OPPORTUNITY / ALIGNMENT logs updated
- [ ] Evidence folder at data/feedback-evidence/batch-YYYY-MM-DD/

### Notes
[Gaps, drift corrections, next alignment target]
```

---

## Alignment Index

| ID | Title | Status | Date |
|----|-------|--------|------|
| ALN-2026-001 | Fleet batch discipline LIVE ↔ M1–M9 cadence | Aligned | 2026-07-10 |

---

## ALN-2026-001: Fleet batch discipline LIVE ↔ M1–M9 cadence

**Date:** 2026-07-10  
**Batch:** batch-2026-07-10  
**Status:** Aligned

### Fleet batch summary

Established batch documentation wrap-up gate (ADR-027): stop dispatch after 5 Done, milestone completion, or 2+ parked blockers; mandatory DEV/DECISION/OPPORTUNITY/ALIGNMENT logs plus evidence folder before resuming Queued work. First opportunities logged for deferred M2 human E2E, M4 OTel/Letta VPS, and M5 live squad webhooks.

### Roadmap alignment

| Milestone | Batch impact | Tier proof |
|-----------|--------------|------------|
| M1 | Staging deploy parity achieved earlier in sprint; batch discipline preserves deploy context | T2 smoke @ `71fd7ae` |
| M2 | Human E2E intentionally deferred — logged as OPP-2026-001, not a dev gate | T3 open |
| M4 | Code complete; VPS enablement deferred — OPP-2026-002 | T0 done, T2 open |
| M5 | Mock squad bridge done; live webhooks deferred — OPP-2026-003 | T0/T2 mock pass |
| M6–M9 | Dashboard MVP (M6.1) shipped in sprint; M7–M9 unchanged | T2 dashboard curl |

### Discipline checks

- [x] Stop trigger defined (5 Done / milestone / 2+ parked blockers)
- [x] DEV / DECISION / OPPORTUNITY / ALIGNMENT logs updated (this setup batch)
- [x] Evidence folder path documented: `data/feedback-evidence/batch-2026-07-10/`
- [x] Resume Queued procedure documented in BATCH-DOCUMENTATION.md

### Notes

Batch documentation discipline **aligns** with [ROADMAP-VALIDATION.md](../operations/ROADMAP-VALIDATION.md) milestone cadence: each M1–M9 closure should trigger wrap-up before the next milestone wave. Human E2E deferral is **aligned** with tier policy (T3 does not block T0/T2). Next alignment check: after M2 sign-off session or next 5-Done fleet batch.

---

*End of alignment log. Add new entries above this line.*