# Opportunities log

**Purpose:** Deferred improvements discovered during implementation, review, or harvest — not yet in ship queue.

**Format:** One section per batch. Promote value ≥7, complexity ≤M to `data/harvest-backlog-advoi.md` or fleet `## Queued`.

**Process:** See [BATCH-DOCUMENTATION.md](../operations/BATCH-DOCUMENTATION.md)

---

## Index

| Date | Batch | OPP count | Promoted |
|------|-------|-----------|----------|
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

## [2026-07-10] — AFK architecture wave + PEL

| ID | Opportunity | Lane | Value | Complexity | Source | Promoted to |
|----|-------------|------|-------|------------|--------|-------------|
| OPP-001 | Playwright PWA connect smoke (no mic) — M3.5 | FEAT | 6 | M | batch / roadmap | parked — not done this wave |
| OPP-002 | `OTEL_ENABLED=true` + collector sidecar on VPS — M4.5 | OPP | 7 | M | moat-review / batch | parked — ops env; not done |
| OPP-003 | Live squad webhooks (`ADVOI_SQUAD_MOCK=false`) — M5.4/M5.5 | FEAT | 7 | M | moat-review / batch | parked — secrets + ACK path |
| OPP-004 | Dedicated `triage.py` classify + richer `needs_review` signals beyond lifecycle API — M7.2 full | FEAT | 6 | M | ingest lifecycle ship | parked — lifecycle partial done |
| OPP-005 | Live cutover `/opt/advoi` → `/var/www/advoi/live` | ARCH | 5 | L | www bootstrap | parked — staging path first |

**Notes:** PWA smoke, OTel, and live webhooks explicitly deferred this wrap-up so the AFK wave can close on PEL + memory + lifecycle without ops blockers.
