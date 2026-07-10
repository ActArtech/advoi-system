# Opportunities log

**Purpose:** Deferred improvements discovered during implementation, review, or harvest — not yet in ship queue.

**Format:** One section per batch. Promote value ≥7, complexity ≤M to `data/harvest-backlog-advoi.md` or fleet `## Queued`.

**Process:** See [BATCH-DOCUMENTATION.md](../operations/BATCH-DOCUMENTATION.md)

---

## Index

| Date | Batch | OPP count | Promoted |
|------|-------|-----------|----------|
| 2026-07-10 | **opp-promote-01** (batch discipline) | — | **3 new Queued + 4 mapped + 1 deferred L** (gate closed) |
| 2026-07-10 | wave 4 Aether/system/arch | 8 | 6 value≥7 resolved (3 promote-new, 3 map, 1 L-defer split); 2 low-value deferred |
| 2026-07-10 | wave 3 PWA interaction | 7+1 | value≥7 mapped/promoted via wave4 canonical + maps |
| 2026-07-10 | wave 2 PWA/analytics/aether | 8 | value≥7 mapped/promoted via wave4 canonical + maps |
| 2026-07-10 | AFK arch wave + PEL | 5 | value≥7 mapped to existing Queued |

---

## [2026-07-10] — batch discipline opp-promote-01

**Crewmate:** `fm/advoi-batch-opp-promote-01` · **Sources:** this log + wave2–4 `data/feedback-evidence/batch-2026-07-10-wave*/summary.md` · **Fleet backlog:** firstmate files cards from `data/advoi-batch-opp-promote-01/firstmate-note.md` (crewmate does **not** write `/data/backlog.md`).

### Gate status: **PASS**

All open value≥7 items either **promoted** (new Queued id or map to existing backlog id) or **explicit deferred** with rationale.

### Canonical value≥7 outcomes (deduped; wave 4 ids preferred)

| Theme | Value | Cx | Outcome | Backlog / note |
|-------|-------|----|---------|----------------|
| Staging promote after SSH host-key fix (GAP-013) | 9 | S | **promoted (new)** | `advoi-ops-staging-promote-01` |
| VPS wire aether-feed-cron + gate-export | 8 | S | **promoted (new)** | `advoi-ops-aether-cron-wire-01` (depends promote) |
| M10.4 PEL rows + gate_snapshot + funnel SQL on staging | 8 | S | **promoted (new)** | `advoi-val-pel-m10-4-proof-01` (depends promote) |
| Human A11–A17 on staging tip | 8 | S | **mapped** | existing `advoi-roadmap-t3-m2-01` (parked T3) |
| `OTEL_ENABLED` + collector T2 (M4.5/M4.6) | 8 | M | **mapped** | existing `advoi-roadmap-t2-m4-05` |
| Live squad webhooks (M5.4/M5.5) | 7 | M | **mapped** | existing `advoi-roadmap-t2-m5-04` |
| M7 Phase 2 triage inbox + batch + voice | 7 | L | **deferred** | complexity **L** — keep classifier `advoi-roadmap-m7-02`; split UI later |
| Funnel SQL live staging (wave3) | 7 | S | **folded** | into `advoi-val-pel-m10-4-proof-01` |

### Low-value / polish (explicit deferred, not promote)

| Theme | Value | Rationale |
|-------|-------|-----------|
| Write-path V4 voice→API routing | 6 | P1 arch polish; Guardian-gated path works; revisit post-promote |
| Write-path V5 aether publish vs vertical rule | 5 | Intentional publish path; wording-only revisit |
| Full Playwright PWA connect smoke M3.5 | 6 | Partial e2e stubs shipped; full connect smoke later |
| Live cutover `/opt` → `/var/www/.../live` | 5 | Staging path first |
| M10.5 PEL query/read API + dashboard | 5 | Write+funnel docs done; read path open, below promote bar |
| Dedicated triage.py polish M7.2 full | 6 | Partial lifecycle done; classifier already Queued as `advoi-roadmap-m7-02` |
| Aether proactive live feed producer | 6 | Needs promote first; cron wire covers install |

---

## Template (copy per batch)

```markdown
## [YYYY-MM-DD] — <batch title>

| ID | Opportunity | Lane | Value | Complexity | Source | Promoted to |
|----|-------------|------|-------|------------|--------|-------------|
| OPP-001 | | OPP | | S/M/L | batch | backlog/harvest/parked |
```

---

_Add entries below newest first._

## [2026-07-10] — wave 4 Aether / system / arch (post-`ff74a98`)

| ID | Opportunity | Lane | Value | Complexity | Source | Promoted to |
|----|-------------|------|-------|------------|--------|-------------|
| OPP-001 | Staging promote develop→staging after SSH host-key fix | OPS | 9 | S | wave2–4 blocker | **promoted** → `advoi-ops-staging-promote-01` (new Queued; firstmate-note) |
| OPP-002 | VPS wire aether-feed-cron + gate-export after promote | OPS | 8 | S | `686fe38`/`e71607f` | **promoted** → `advoi-ops-aether-cron-wire-01` (depends OPP-001) |
| OPP-003 | M10.4 PEL rows + gate_snapshot / funnel SQL on staging | VAL | 8 | S | M10 / wave4 | **promoted** → `advoi-val-pel-m10-4-proof-01` (depends OPP-001) |
| OPP-004 | Human A11–A17 on staging tip | VAL | 8 | S | wave3 | **promoted** → existing `advoi-roadmap-t3-m2-01` (T3 parked) |
| OPP-005 | Write-path V4: thin voice→API routing (no direct fleet import) | ARCH | 6 | M | audit V4 | **deferred** — value 6; still Guardian-gated via `fleet_trigger_from_voice` |
| OPP-006 | Write-path V5: resolve aether atomic publish vs “no fleet tree write” rule | ARCH | 5 | M | audit V5 | **deferred** — value 5; intentional publish; revisit vertical wording |
| OPP-007 | `OTEL_ENABLED` + collector T2 — M4.5/M4.6 | OPP | 8 | M | wave2 | **promoted** → existing `advoi-roadmap-t2-m4-05` (code @ `697b897`) |
| OPP-008 | M7 Phase 2 triage inbox + batch + voice; live squad webhooks M5 | FEAT | 7 | L/M | roadmap | **split:** M5 → `advoi-roadmap-t2-m5-04`; M7 Phase 2 UI → **deferred** (complexity L; classifier stays `advoi-roadmap-m7-02`) |

**Notes:** Wave 4 closed the Aether Queued slice (feed skip, atomic publish, gate export) and Guardian write-path P0 hard-gate (ADR-028). **opp-promote-01 (2026-07-10):** value≥7 gate closed — 3 new ops/val Queued cards + maps to existing roadmap Queued; M7 Phase 2 UI explicit deferred (L).

## [2026-07-10] — wave 3 PWA interaction slice (post-`727f77f`)

| ID | Opportunity | Lane | Value | Complexity | Source | Promoted to |
|----|-------------|------|-------|------------|--------|-------------|
| OPP-001 | Human A14–A17 on staging tip (gate / confirm / install / briefs) | VAL | 8 | S | wave3 | **promoted** → existing `advoi-roadmap-t3-m2-01` (= wave4 OPP-004) |
| OPP-002 | Staging promote develop→staging after SSH host-key fix | OPS | 9 | S | wave2/3 blocker | **promoted** → `advoi-ops-staging-promote-01` (= wave4 OPP-001) |
| OPP-003 | Funnel SQL against live staging PEL (connect→success) | OPP | 7 | S | `12b1ad8` | **promoted** → folded into `advoi-val-pel-m10-4-proof-01` |
| OPP-004 | Full Playwright PWA connect smoke (no mic) — M3.5 | FEAT | 6 | M | roadmap | **deferred** — value 6; e2e stubs partial; full connect smoke open |
| OPP-005 | `OTEL_ENABLED=true` + collector T2 — M4.5/M4.6 | OPP | 8 | M | wave2 | **promoted** → existing `advoi-roadmap-t2-m4-05` |
| OPP-006 | Live squad webhooks — M5.4/M5.5 | FEAT | 7 | M | prior | **promoted** → existing `advoi-roadmap-t2-m5-04` |
| OPP-007 | M7 Phase 2: triage inbox UI + batch upload + voice triage | FEAT | 7 | L | roadmap | **deferred** — complexity L; not PWA scope; classifier `advoi-roadmap-m7-02` only |
| OPP-008 | M10.5 PEL query/read API + dashboard last_dispatch | FEAT | 5 | M | analytics | **deferred** — value 5; write + funnel docs done; read path open |

**Notes:** Wave 3 closed the PWA interaction Queued slice on develop. **opp-promote-01:** all value≥7 rows promoted or explicit deferred; low-value M3.5/M10.5 deferred with rationale.

## [2026-07-10] — wave 2 PWA / analytics / aether (post-`b2ced10`)

| ID | Opportunity | Lane | Value | Complexity | Source | Promoted to |
|----|-------------|------|-------|------------|--------|-------------|
| OPP-001 | Full Playwright PWA connect smoke (no mic) — M3.5 | FEAT | 6 | M | roadmap | **deferred** — value 6; state/latency/recovery e2e stubs only |
| OPP-002 | `OTEL_ENABLED=true` + collector on VPS — M4.5/M4.6 T2 | OPP | 8 | M | wave2 / moat R6 | **promoted** → existing `advoi-roadmap-t2-m4-05` (code @ `697b897`) |
| OPP-003 | Live squad webhooks (`ADVOI_SQUAD_MOCK=false`) — M5.4/M5.5 | FEAT | 7 | M | prior wave | **promoted** → existing `advoi-roadmap-t2-m5-04` |
| OPP-004 | Dedicated `triage.py` classifier polish — M7.2 full | FEAT | 6 | M | prior wave | **deferred** — value 6; lifecycle partial; classifier Queued `advoi-roadmap-m7-02` |
| OPP-005 | Live cutover `/opt/advoi` → `/var/www/advoi/live` | ARCH | 5 | L | www bootstrap | **deferred** — value 5 L; staging path first |
| OPP-006 | Staging promote + OTEL/PEL T2 after SSH host-key fix | OPS | 9 | S | wave2 blocker | **promoted** → `advoi-ops-staging-promote-01` (+ OTEL/PEL as separate mapped/new cards) |
| OPP-007 | Aether proactive live feed on VPS (schema T0 done) | FEAT | 6 | M | `ce6a8e2` | **deferred** — value 6; cron wire `advoi-ops-aether-cron-wire-01` covers VPS install post-promote |
| OPP-008 | M10.5 query API / dashboard last_dispatch from PEL | FEAT | 5 | M | beacon ship | **deferred** — value 5; write path done; read path open |

**Notes:** Wave 2 closed 8 code Done items. **opp-promote-01:** value≥7 promoted/mapped; remainder explicit deferred.

## [2026-07-10] — AFK architecture wave + PEL

| ID | Opportunity | Lane | Value | Complexity | Source | Promoted to |
|----|-------------|------|-------|------------|--------|-------------|
| OPP-001 | Playwright PWA connect smoke (no mic) — M3.5 | FEAT | 6 | M | batch / roadmap | **deferred** — value 6; not done this wave |
| OPP-002 | `OTEL_ENABLED=true` + collector sidecar on VPS — M4.5 | OPP | 7 | M | moat-review / batch | **promoted** → existing `advoi-roadmap-t2-m4-05` |
| OPP-003 | Live squad webhooks (`ADVOI_SQUAD_MOCK=false`) — M5.4/M5.5 | FEAT | 7 | M | moat-review / batch | **promoted** → existing `advoi-roadmap-t2-m5-04` |
| OPP-004 | Dedicated `triage.py` classify + richer `needs_review` signals beyond lifecycle API — M7.2 full | FEAT | 6 | M | ingest lifecycle ship | **deferred** — value 6; lifecycle partial; `advoi-roadmap-m7-02` |
| OPP-005 | Live cutover `/opt/advoi` → `/var/www/advoi/live` | ARCH | 5 | L | www bootstrap | **deferred** — value 5 L; staging path first |

**Notes:** AFK wave closed on PEL + memory + lifecycle. **opp-promote-01:** value≥7 OTEL/webhooks mapped to roadmap Queued; low-value explicit deferred.
