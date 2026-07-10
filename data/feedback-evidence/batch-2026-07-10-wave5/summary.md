# Batch wrap-up — wave 5 post–wave-4 lands (2026-07-10)

**Batch:** Memory / fleet / ingest / www / M7–M9 docs + ops discipline  
**Captain:** First Mate (crewmate wrap-up `advoi-batch-wrapup-wave5-01`)  
**Status:** **Partial** — code + docs complete on develop; staging VPS promote **parked** (GAP-013 SSH host key)  
**Develop tip:** `9065b94`  
**Prior wrap-up:** wave 4 tip `61de279` / wrap-up docs `4dd24f6`  
**Staging SHA:** `5d50805` (unchanged — promote blocked)

## Done items this wave (post-`4dd24f6` → `9065b94`)

| Theme | Key SHA(s) | Notes |
|-------|------------|-------|
| Data authority matrix | `792f957` | `04-memory-and-data` authority matrix |
| Versioned SQL migrations | `19b052d` | Migrations applied on API boot |
| Staging drift record | `fd9094d` `382864a` | develop ahead of VPS `5d50805`; T2 ≠ tip parity |
| Paperclip ingest field | `3d5a00d` | optional `paperclip_ticket_id` on IngestItem |
| Aether DECISIONS stubs | `2b9a28e` | venture-facing ADR-027/028 |
| Roadmap/gaps sync + opp-promote | `741e961` `ba3e436` | tip sync; value≥7 OPPs promote/defer gate |
| Memory guard (Hindsight) | `7a6cc98` | reject fleet backlog payloads on retain (ADR-026) |
| Ontology route errors | `2511eba` | 422 structured errors for unknown frame_id/agent_id |
| review_queue Postgres | `432f1a2` | complete CRUD + redeploy durability |
| Retain metrics | `c666f85` | WARNING on retain failure + platform diagnostics counter |
| Trace correlation | `1c729f0` | guardian JSONL ↔ OTel span context |
| post_frame retain types | `9cd0aa6` | align with ADR-026 write_targets |
| Fleet bridge | `4fe946f` | wake_firstmate → fm-bridge path + T0 subprocess tests |
| www three-tier scripts | `40f20f3` | vendor promote-to-staging + compose.www.yml |
| Ontology/ingest venture gate | `d91903b` | reject unregistered venture_id on route |
| Ingest UI lifecycle | `59da773` | triage → approve → dispatch parity |
| TTL retention | `04b276e` | Redis voice TTL env + memory_events retention job |
| M7.2 triage | `40af47c` | keyword triage classifier (`triage.py`) |
| Logic flow diagram | `a37d7e7` | Mermaid five control-plane flows |
| frame_runner doc | `a097692` | resolution precedence |
| M8 Discord workflow | `d294846` | ACK PROMOTE NEXT (FirstMate) |
| M9.1 port registry | `9065b94` | aligned with vps-shared |

**Also in range (ops continuity):** staging-record / ops-review alignment rows already in ALIGNMENT-LOG; harvest-baseline scout not a separate tip SHA in this range (covered under fleet/www ops scripts if present on tree).

## Milestone

**Post–wave-4 platform depth** on develop: memory retain observability + review_queue durability, fleet wake bridge complete at T0, ingest ontology hardening + M7.2 triage + lifecycle UI, www promote path for three-tier, M8/M9 ops docs. **Not** a single roadmap M-signoff; advances **M7 partial**, **M8/M9 docs**, **memory/ops readiness** for post-promote T2.

## Smoke / T0

| Check | Result |
|-------|--------|
| Full pytest collection | **625** tests |
| Wave5 suite subset | **207 passed** (see `pytest-wave5.txt`) |
| Keyword filter | retain / review_queue / memory / fleet_bridge / wake / triage / ingest / ontology / retention / ttl / paperclip / migration / hindsight / otel / … |
| Staging live T2 | **Not re-run** — SSH host key verification failed on promote (GAP-013) |
| Bootstrap T2 (prior) | Pass 2026-07-10 @ staging `5d50805` |

## Blockers parked

1. **Staging VPS promote (GAP-013)** — SSH host key verification failed  
   - Staging remains @ `5d50805`  
   - Develop @ `9065b94`  
   - Blocks: tip T2 for wave 2–5 code, M10.4 PEL, OTEL apply, migrations/review_queue/TTL on VPS, human A11–A17 on real tip  
2. **M2 human E2E** — still open (device); includes A11–A17  
3. **M5 live webhooks / M4.4 Letta / M7 Phase 2 batch UI** — deferred (OPP), not wave5 exclusive scope  

## Decisions

- No new ADR this wrap-up. Wave5 implements ADR-026 (retain targets / Hindsight guard), ADR-027 (PEL authority already staged), ADR-028 (write-path gate already landed wave4).  
- **opp-promote-01** closed value≥7 gate (promoted Queued cards + explicit L defer for M7 Phase 2 UI) — see OPPORTUNITIES-LOG.

## Logs updated

- `docs/dev-log/DEV-LOG.md` — wave 5 entry  
- `docs/current-state/ALIGNMENT-LOG.md` — wave 5 row develop `9065b94` vs staging `5d50805`  
- `docs/current-state/gaps-and-blockers.md` — tip SHA → `9065b94`  
- Evidence: this folder  

## Next Queued slice (after wrap-up merge)

1. Fix SSH known_hosts / host key for deploy host (**GAP-013** / `advoi-ops-staging-promote-01`)  
2. Promote develop → staging; `t2-staging-smoke.sh` + full precheck on tip  
3. Prove M10.4 + gate_export / funnel / review_queue / TTL retention on staging  
4. Optional OTEL apply; aether feed cron wire  
5. Human E2E M2 including A11–A17 when device available  
6. Resume Queued fleet dispatch  

## Resume condition

Mandatory BATCH-DOCUMENTATION artifacts present on branch `fm/advoi-batch-wrapup-wave5-01`. Firstmate merges to `develop` (no PR / VPS-direct). Queued dispatch may resume after merge.
