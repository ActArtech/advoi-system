# Evidence — batch-2026-07-10-wave5

**What this batch proved:** Post–wave-4 landings on develop (`4dd24f6`..`9065b94`): memory guard + review_queue PG + retain metrics/trace correlation, post_frame ADR-026 retain alignment, fleet wake_firstmate bridge, www three-tier promote scripts, ontology/ingest route hardening, ingest UI lifecycle + M7.2 triage, TTL retention, architecture/ops docs (logic flow, frame_runner, M8 Discord, M9 port registry), opp-promote + staging-record discipline. Wave5 T0 subset **207 passed**; full tree **625** collected.

**Develop tip:** `9065b94`  
**Prior wrap-up:** wave 4 @ `61de279` / wrap-up docs `4dd24f6`  
**Staging:** not re-proven — SSH promote still parked (`5d50805` vs develop `9065b94`). See `blockers.md` (GAP-013).

| File | Content |
|------|---------|
| `summary.md` | Wrap-up narrative, Done themes, next steps |
| `blockers.md` | GAP-013 SSH promote park + non-blockers |
| `done-items.txt` | `git log 4dd24f6..9065b94` |
| `pytest-wave5.txt` | Wave suite T0 output (207 passed) |
| `pytest-collect.txt` | Full collection count (625) |
