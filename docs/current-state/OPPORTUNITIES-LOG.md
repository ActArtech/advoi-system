# Opportunities log

**Purpose:** Deferred improvements discovered during implementation, review, or harvest — not yet in ship queue.

**Format:** One section per batch. Promote value ≥7, complexity ≤M to `data/harvest-backlog-advoi.md` or fleet `## Queued`.

**Process:** See [BATCH-DOCUMENTATION.md](../operations/BATCH-DOCUMENTATION.md)

---

## Index

| Date | Batch | OPP count | Promoted |
|------|-------|-----------|----------|
| 2026-07-10 | wave 4 Aether/system/arch | 8 | 0 (parked; code complete) |
| 2026-07-10 | wave 3 PWA interaction | 7 | 0 (parked; code complete) |
| 2026-07-10 | wave 2 PWA/analytics/aether | 6 | 0 (parked; partial code progress) |
| 2026-07-10 | AFK arch wave + PEL | 5 | 0 (parked) |

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
| OPP-001 | Staging promote develop→staging after SSH host-key fix | OPS | 9 | S | wave2–4 blocker | **parked** — staging `5d50805` vs develop `61de279` |
| OPP-002 | VPS wire aether-feed-cron + gate-export after promote | OPS | 8 | S | `686fe38`/`e71607f` | parked — needs SSH + cron install |
| OPP-003 | M10.4 PEL rows + gate_snapshot / funnel SQL on staging | VAL | 8 | S | M10 / wave4 | parked — needs promote + traffic |
| OPP-004 | Human A11–A17 on staging tip | VAL | 8 | S | wave3 | parked — device + SSH promote |
| OPP-005 | Write-path V4: thin voice→API routing (no direct fleet import) | ARCH | 6 | M | audit V4 | parked — still Guardian-gated via `fleet_trigger_from_voice` |
| OPP-006 | Write-path V5: resolve aether atomic publish vs “no fleet tree write” rule | ARCH | 5 | M | audit V5 | parked — intentional publish; revisit vertical rules |
| OPP-007 | `OTEL_ENABLED` + collector T2 — M4.5/M4.6 | OPP | 8 | M | wave2 | code done; VPS apply parked (SSH) |
| OPP-008 | M7 Phase 2 triage inbox + batch + voice; live squad webhooks M5 | FEAT | 7 | L | roadmap | **unchanged** — not wave4 scope |

**Notes:** Wave 4 closed the Aether Queued slice (feed skip, atomic publish, gate export) and Guardian write-path P0 hard-gate (ADR-028). Hard parked blocker remains SSH promote. Deferred audit V4/V5 are architecture polish, not blockers to resume Queued.

## [2026-07-10] — wave 3 PWA interaction slice (post-`727f77f`)

| ID | Opportunity | Lane | Value | Complexity | Source | Promoted to |
|----|-------------|------|-------|------------|--------|-------------|
| OPP-001 | Human A14–A17 on staging tip (gate / confirm / install / briefs) | VAL | 8 | S | wave3 | parked — device + SSH promote |
| OPP-002 | Staging promote develop→staging after SSH host-key fix | OPS | 9 | S | wave2/3 blocker | **parked** — staging `5d50805` vs develop `587385d` |
| OPP-003 | Funnel SQL against live staging PEL (connect→success) | OPP | 7 | S | `12b1ad8` | parked — needs promote + traffic |
| OPP-004 | Full Playwright PWA connect smoke (no mic) — M3.5 | FEAT | 6 | M | roadmap | **partial** — more e2e stubs (gate/confirm/onboarding/briefs); full connect smoke open |
| OPP-005 | `OTEL_ENABLED=true` + collector T2 — M4.5/M4.6 | OPP | 8 | M | wave2 | code done; VPS apply parked (SSH) |
| OPP-006 | Live squad webhooks — M5.4/M5.5 | FEAT | 7 | M | prior | parked |
| OPP-007 | M7 Phase 2: triage inbox UI + batch upload + voice triage | FEAT | 7 | L | roadmap | **unchanged** — not in PWA interaction scope |
| OPP-008 | M10.5 PEL query/read API + dashboard last_dispatch | FEAT | 5 | M | analytics | parked — write + funnel docs done; read path open |

**Notes:** Wave 3 closed the PWA interaction Queued slice on develop (gate chip, confirm parity, onboarding, home briefs, funnel doc). Hard parked blocker remains SSH promote. M7 ingestion Phase 2 intentionally untouched this wave. Human matrix A11–A17 ready for device once staging has tip.

## [2026-07-10] — wave 2 PWA / analytics / aether (post-`b2ced10`)

| ID | Opportunity | Lane | Value | Complexity | Source | Promoted to |
|----|-------------|------|-------|------------|--------|-------------|
| OPP-001 | Full Playwright PWA connect smoke (no mic) — M3.5 | FEAT | 6 | M | roadmap | **partial** — state/latency/recovery e2e stubs shipped; full connect smoke still open |
| OPP-002 | `OTEL_ENABLED=true` + collector on VPS — M4.5/M4.6 T2 | OPP | 8 | M | wave2 / moat R6 | **code done** @ `697b897`; VPS apply **parked** (SSH host key) |
| OPP-003 | Live squad webhooks (`ADVOI_SQUAD_MOCK=false`) — M5.4/M5.5 | FEAT | 7 | M | prior wave | parked — secrets + ACK path |
| OPP-004 | Dedicated `triage.py` classifier polish — M7.2 full | FEAT | 6 | M | prior wave | parked — lifecycle API partial |
| OPP-005 | Live cutover `/opt/advoi` → `/var/www/advoi/live` | ARCH | 5 | L | www bootstrap | parked — staging path first |
| OPP-006 | Staging promote + OTEL/PEL T2 after SSH host-key fix | OPS | 9 | S | wave2 blocker | **parked** — staging `5d50805` vs develop `ce6a8e2` |
| OPP-007 | Aether proactive live feed on VPS (schema T0 done) | FEAT | 6 | M | `ce6a8e2` | parked — needs promote + feed producer |
| OPP-008 | M10.5 query API / dashboard last_dispatch from PEL | FEAT | 5 | M | beacon ship | parked — write path (beacon) done; read path open |

**Notes:** Wave 2 closed 8 code Done items on develop. Ops promote is the only hard parked blocker (SSH host key verification failed). OTEL/trace_id and T2 smoke script are code-ready; re-run T2 after promote. Human E2E A11–A13 (state chip, latency chip, error recovery) remain device-side.

## [2026-07-10] — AFK architecture wave + PEL

| ID | Opportunity | Lane | Value | Complexity | Source | Promoted to |
|----|-------------|------|-------|------------|--------|-------------|
| OPP-001 | Playwright PWA connect smoke (no mic) — M3.5 | FEAT | 6 | M | batch / roadmap | parked — not done this wave |
| OPP-002 | `OTEL_ENABLED=true` + collector sidecar on VPS — M4.5 | OPP | 7 | M | moat-review / batch | parked — ops env; not done |
| OPP-003 | Live squad webhooks (`ADVOI_SQUAD_MOCK=false`) — M5.4/M5.5 | FEAT | 7 | M | moat-review / batch | parked — secrets + ACK path |
| OPP-004 | Dedicated `triage.py` classify + richer `needs_review` signals beyond lifecycle API — M7.2 full | FEAT | 6 | M | ingest lifecycle ship | parked — lifecycle partial done |
| OPP-005 | Live cutover `/opt/advoi` → `/var/www/advoi/live` | ARCH | 5 | L | www bootstrap | parked — staging path first |

**Notes:** PWA smoke, OTel, and live webhooks explicitly deferred this wrap-up so the AFK wave can close on PEL + memory + lifecycle without ops blockers.
