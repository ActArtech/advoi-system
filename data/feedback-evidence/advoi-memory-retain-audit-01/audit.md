# ADR-026 retain integrity audit

**Task:** `advoi-memory-retain-audit-01` (Architecture ship #2a)  
**Branch:** `fm/advoi-memory-retain-audit-01`  
**Scope:** Every `MemoryRouter.retain()` / `retain_strategic` / direct Hindsight call  
**Out of scope:** Brief Curator triple-path (`advoi-memory-brief-triple-path-01`)  
**Reference:** ADR-026 (`docs/decision-log/DECISION-LOG.md`), `advoi/memory/write_targets.py`  
**Note:** `docs/reviews/ARCHITECTURE-DATA-MEMORY-REVIEW.md` is not present; used `docs/architecture/04-memory-and-data.md` Gaps + ADR-026 Never-rules.

## Rules (ADR-026)

| Store | Allowed content |
|-------|-----------------|
| Hindsight | portfolio facts, governance, cross-project synthesis, venture beliefs |
| Letta | agent identity, user prefs, squad operational learning |
| Postgres | structured canonical (projects, briefs, master-state) |
| Redis | ephemeral turn window + rolling summary |
| Guardian | error / recovery log only |
| **Never** | Guardian errors → beliefs; **fleet backlog → memory** |

All production retains must go through `MemoryRouter.retain(MemoryEventType, …)` so `EVENT_WRITE_MAP` selects targets.

---

## Inventory: `MemoryRouter.retain` call sites

| File:line | Event type | In EVENT_WRITE_MAP? | Targets | Notes |
|-----------|------------|---------------------|---------|-------|
| `advoi/aether/architect.py:70` | `SQUAD_LESSON` | yes | Letta, Postgres | Post-frame operational |
| `advoi/aether/architect.py:81` | `VENTURE_BELIEF_UPDATE` | yes | Hindsight | Strategic; summary is `{venture}: {frame} ran OK` — not backlog |
| `advoi/squads/dispatch.py:53` | `SQUAD_LESSON` | yes | Letta, Postgres | Squad job queue |
| `advoi/routing/agent_bootstrap.py:49` | `SQUAD_LESSON` | yes | Letta, Postgres | Includes fleet-scout spoken_summary — **operational only** |
| `advoi/voice/memory_hooks.py:20` | `VOICE_TURN` | yes | Redis | Ephemeral |
| `advoi/squads/orchestrate.py` (fixed) | `WORKFLOW_EVOLUTION` | yes | Letta | Was direct `retain_operational_unified("orchestration_run")` |
| `tests/test_memory.py:43` | `PORTFOLIO_FACT` | yes | Hindsight, Postgres | Test only |

## Inventory: `retain_strategic` / direct Hindsight

| File:line | Kind | Allowed? | Notes |
|-----------|------|----------|-------|
| `advoi/memory/router.py:112-116` | imports + calls `retain_strategic` | **yes** | Sole app entry when `WriteTarget.HINDSIGHT` |
| `advoi/memory/hindsight.py:82-114` | `_retain_direct` → `client.aretain` | **yes** | Implementation |
| `advoi/memory/hindsight.py:218-242` | `retain_strategic` | **yes** | Public API for router only |
| `advoi/memory/bridge_server.py:66-73` | HTTP `POST /retain` | **infra** | Bridge surface; no EVENT_WRITE_MAP gate |
| `scripts/hindsight-bridge.py:55-73` | `client.aretain` | **infra** | Hermes-side bridge |
| `scripts/seed-advoi-briefs.sh:18-34` | bridge retain `decision_brief` | **flagged** | Bypasses map (`DECISION_BRIEF` → Postgres only). Deferred to brief triple-path |
| `scripts/memory-setup-hindsight.sh:144` | example `portfolio_fact` retain | **ok** | Ops warmup; correct event type |

No other `from advoi.memory.hindsight import retain_strategic` outside `router.py`.

## Inventory: other retain paths (non-Hindsight)

| File:line | Path | Uses MemoryEventType? | Severity |
|-----------|------|----------------------|----------|
| `advoi/squads/orchestrate.py` (pre-fix) | `retain_operational_unified("orchestration_run")` | **no** | **P1 fixed** → router + `WORKFLOW_EVOLUTION` |
| `advoi/guardian/recovery.py:36,40` | `append_guardian_event(...)` free-form | no | Info — correct store; free-form labels |
| `advoi/guardian/notifications.py:33,46` | `append_guardian_event(...)` free-form | no | Info |
| `advoi/guardian/auto_restart.py:57` | `append_guardian_event(...)` free-form | no | Info |
| `advoi/memory/router.py:118-133` | operational / postgres / redis / guardian | yes (via map) | OK |

## Fleet backlog → strategic check

| Check | Result |
|-------|--------|
| `retain_strategic` / Hindsight payloads with fleet backlog text | **None found** |
| `VENTURE_BELIEF_UPDATE` payload shape | Generic “ran OK” only (`architect.py`) |
| fleet-scout / run_next_backlog content in retains | Only as `SQUAD_LESSON` operational (agent_bootstrap) — **not Hindsight** |
| ADR Never: fleet backlog → memory (strategic) | **No P0 leak** |

## Violations summary

| ID | Severity | Description | Action |
|----|----------|-------------|--------|
| V1 | **P1** (fixed) | `orchestrate.retain_orchestration_memory` called `retain_operational_unified` with free-form `"orchestration_run"` outside `MemoryEventType` / `EVENT_WRITE_MAP` | Route via `MemoryRouter.retain(WORKFLOW_EVOLUTION, …)` |
| V2 | **Flagged / deferred** | `seed-advoi-briefs.sh` retains `decision_brief` into Hindsight; map says Postgres only | No Brief Curator changes this task |
| V3 | Info | Guardian free-form event strings not in `MemoryEventType` | Store correct; optional follow-up to use `RUNTIME_ERROR` / `RECOVERY_NOTE` |
| V4 | Info | Bridge HTTP/script accept any `event_type` without map validation | Infra; trust callers |

### Counts

| Metric | Count |
|--------|------:|
| **P0 Hindsight / fleet-backlog leaks** | **0** |
| **P1 fixed this ship** | **1** (V1) |
| **Flagged deferred** | **1** (V2) |
| **Info** | **2** (V3, V4) |
| **Production `MemoryRouter.retain` sites** | **6** (all map-valid after fix) |

## Guardrails added

- `tests/test_memory_retain_audit.py` — static assertions that forbidden patterns stay absent/guarded
- This report under `data/feedback-evidence/advoi-memory-retain-audit-01/audit.md`
