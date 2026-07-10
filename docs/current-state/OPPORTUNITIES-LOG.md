# Opportunities log

**Purpose:** Deferred improvements discovered during implementation, review, or harvest — not yet in ship queue.

**Format:** One section per batch. Promote value ≥7, complexity ≤M to `data/harvest-backlog-advoi.md` or fleet `## Queued`.

**Process:** See [BATCH-DOCUMENTATION.md](../operations/BATCH-DOCUMENTATION.md)

---

## Index

| Date | Batch | OPP count | Promoted |
|------|-------|-----------|----------|
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
