# Multi-agent architecture

Runtime ships **six specialist agents**, each bound to one **decision frame** (PWA Options A–F). They run as background daemons and cache results for fast PWA/voice responses. Parallel refresh is available via `POST /api/agents/run-six`.

> **Doc sync:** Reconciled with `advoi/routing/agents.py` + `advoi/decision/frames.py` (6 agents / 6 frames). Companion review: [ARCHITECTURE-DATA-MEMORY-REVIEW.md](../reviews/ARCHITECTURE-DATA-MEMORY-REVIEW.md) (closes *Routing/Decision **Stale***; unblocks M9.4 / GAP-012).

## Agents and frames

| Option | Agent ID | Name | Frame ID | Role | Confirmation |
|--------|----------|------|----------|------|--------------|
| A | `fleet-scout` | Fleet Scout | `fleet_status` | Read-only FirstMate / Hermes fleet status | No |
| B | `brief-curator` | Brief Curator | `open_briefs` | Surface open decision briefs from memory and backlog | No |
| C | `review-queue` | Review Queue | `queue_deep_review` | Queue async deep review for desktop follow-up (not live execution) | **Yes** (Guardian) |
| D | `systems-pulse` | Systems Pulse | `systems_pulse` | Orchestrate fleet, briefs, and agent cache in one parallel pass | No |
| E | `memory-scout` | Memory Scout | `memory_health` | Probe Hindsight bridge, Redis, Postgres, and operational store health | No |
| F | `guardian-sentinel` | Guardian Sentinel | `guardian_status` | Surface confirmation policy and recent guardian events | No |

| Frame ID | PWA / catalog label | Voice prompt |
|----------|---------------------|--------------|
| `fleet_status` | Option A: Fleet status | Give me a quick fleet status update. |
| `open_briefs` | Option B: Open briefs | What decision briefs are open right now? |
| `queue_deep_review` | Option C: Queue deep review | Queue a deep review for the top priority item. |
| `systems_pulse` | Option D: Systems pulse | Give me a full systems pulse across fleet and briefs. |
| `memory_health` | Option E: Memory health | How is the memory stack doing? |
| `guardian_status` | Option F: Guardian status | What is the guardian and safety status? |

Source of truth: `advoi/routing/agents.py` (`AGENTS`), `advoi/decision/frames.py` (`FRAMES`). Staging: `GET /api/agents` reports `ready: 6`, `total: 6`.

## Execution flow

```mermaid
flowchart TD
  subgraph triggers [Triggers]
    BTN[PWA frame button]
    DC[LiveKit data channel frame]
    TICK[Agent daemon tick]
    SIX[POST /api/agents/run-six]
  end

  subgraph core [Core]
    FR[run_frame in frame_runner.py]
    ORCH[run_systems_pulse / orchestrator]
    CACHE[Redis advoi:agent:ID:last]
  end

  subgraph backends [Data sources]
    FM[FirstMate fleet files]
    PG[(Postgres decision_briefs / review_queue)]
    RD[(Redis advoi:briefs:open)]
    HS[Hindsight via bridge]
    GUARD[Guardian confirm + event log]
    DIAG[diagnostics probes]
  end

  BTN --> API[POST /api/frames/id/run]
  DC --> FD[frame_dispatch.py]
  TICK --> FR
  SIX --> ORCH
  API --> FR
  FD --> FR
  ORCH --> FR
  FR --> FM
  FR --> PG
  FR --> RD
  FR --> HS
  FR --> GUARD
  FR --> DIAG
  FR --> CACHE
```

## Frame runner behavior

`advoi/routing/frame_runner.py` dispatches all six frames (plus diagnostic helpers):

| Frame | Backend | Behavior |
|-------|---------|----------|
| `fleet_status` | Fleet Scout | Reads fleet snapshot from `FIRSTMATE_FLEET_PATH` (profile, backlog, state, Aether gate). Mock via `ADVOI_FRAME_MOCK=true`. |
| `open_briefs` | Brief Curator | Postgres `decision_briefs` (canonical) → Redis `advoi:briefs:open` (cache fill/invalidate) → optional Hindsight enrich when empty. Mock mode available. |
| `queue_deep_review` | Review Queue | **Built** — Guardian `evaluate_frame_confirmation`; on confirm, `enqueue_review` → Postgres `review_queue` + desktop brief URL (`ADVOI_DESKTOP_BRIEF_BASE_URL`). Not a stub. |
| `systems_pulse` | Systems Pulse | `advoi/routing/orchestrator.py` — parallel specialist pass; post-frame Aether enrich via `post_frame_aether`. |
| `memory_health` | Memory Scout | `advoi/routing/diagnostic_frames.run_memory_health` — bridge, Redis, Postgres, operational store probes. |
| `guardian_status` | Guardian Sentinel | `run_guardian_status` — confirmation policy, high-risk frames/actions, recent guardian event log tail. |

### Resolution precedence (`run_frame`)

Source: `advoi/routing/frame_runner.run_frame` + `advoi/cache/agent_cache.py`.

Every on-demand or daemon call follows this order. **Mock is not checked before the agent cache** — it short-circuits only after a cache miss/bypass, inside the backend runner.

```text
1. Validate frame_id + agent_id (raise if unknown catalog id)
2. Agent cache (Redis) — unless bypassed
3. Backend by frame.id
   3a. ADVOI_FRAME_MOCK short-circuit (fleet / briefs / review only)
   3b. Live data sources + per-frame fallbacks
4. Voice preamble (all frames except open_briefs), Aether enrich, PEL emit
```

| Step | When it runs | Outcome |
|------|--------------|---------|
| **1. Validate** | Always | Unknown frame/agent → exception before any I/O |
| **2. Agent cache** | `use_cache=True` **and** `not refresh` **and** `not confirmed` | Hit only if Redis payload exists, `status == "ok"`, and spoken text is not a fleet-error pattern → return immediately with `detail.cached=true` |
| **3. Refresh / bypass** | `refresh=true` **or** `confirmed=true` **or** `use_cache=false` | Skip step 2; always execute backend |
| **4. Mock** | Cache miss/bypass **and** `ADVOI_FRAME_MOCK` in `{1,true,yes}` | Synthetic `ok` result for `fleet_status`, `open_briefs`, `queue_deep_review` (no fleet/PG I/O). Diagnostics / systems_pulse use live helpers. |
| **5. Backends** | Cache miss/bypass and mock off (or frame has no mock) | Frame-specific live path (table below) |

**Flags** (`run_frame` kwargs / API query):

| Flag | Effect |
|------|--------|
| `refresh=true` | Bypass agent cache; re-run backend (daemon fleet-scout always ticks with refresh) |
| `confirmed=true` | Bypass agent cache (forces live confirm path for review queue) |
| `use_cache=false` | Bypass agent cache without implying refresh semantics elsewhere |

#### Cache keys

| Key | Role | TTL / write rules |
|-----|------|-------------------|
| `advoi:agent:{agent_id}:last` | Last specialist result for PWA/voice fast path | TTL = `2 * ADVOI_AGENT_INTERVAL_SECS` (default 45 → **90s**). Written by `tick_agent` via `write_agent_cache` only when `status` ∈ `{ok, confirmation_required}`. Payload: `agent_id`, `frame_id`, `status`, `spoken_summary`, `timestamp`. |
| `advoi:briefs:open` | Brief-list **data** cache (not agent spoken result) | Filled from Postgres on hit; invalidated when PG returns empty; served only if PG unavailable |

Cache **read** rejection (`_cached_frame`): missing Redis client/key, parse errors, non-`ok` status (caller only accepts `ok`), or spoken text matching fleet-error patterns (`error:`, container not running, fleet bridge not configured, timed out) — treated as miss so the next backend run can recover.

#### Backend fallbacks (after cache / mock)

| Frame | Live path and failure behavior |
|-------|--------------------------------|
| `fleet_status` | Disk snapshot under `FIRSTMATE_FLEET_PATH` → optional `fm-advanced-status.sh` enrich (timeout/missing → keep disk summary, set `advanced_error`). Missing fleet data → status `error`. Spoken `ERROR:` / container-not-running → status `error` (not cached as ok by daemons). |
| `open_briefs` | Postgres canonical → fill Redis; PG down → Redis degraded cache; both empty → optional Hindsight recall enrich; still empty → spoken “no briefs…” with `briefs: []`, status `ok`. |
| `queue_deep_review` | Guardian gate first (`confirmed=false` → `confirmation_required`, no enqueue). On proceed: `enqueue_review`; `queue_id is None` → still spoken as queued, `persistence: unavailable`. Mock skips DB. |
| `systems_pulse` | Parallel `fleet_status` + `open_briefs` (same refresh flag); `degraded` if either child ≠ `ok`. No separate agent-cache read at pulse level. |
| `memory_health` / `guardian_status` | Diagnostic probes only; no `ADVOI_FRAME_MOCK` branch in frame_runner. |

After a successful backend run, callers that warm the cache (`agent_daemon` / `tick_agent`) write `advoi:agent:{id}:last`. Interactive `run_frame` itself does **not** write the agent cache — it only reads.

### Review queue (built, not stub)

1. Frame requires confirmation (`requires_confirmation=True` on Option C).
2. Guardian confirmation gate (`advoi/guardian/confirmation.py`) blocks until voice confirm or double-tap.
3. On proceed: `advoi/memory/review_queue.enqueue_review` persists to Postgres and returns a desktop brief URL.
4. Mock mode still returns a synthetic queue id + URL without DB.

## Daemon deployment

### Docker (production / staging)

Six compose services, same image as API (`docker-compose.yml`, profile `app`):

```yaml
advoi-agent-fleet     → python -m advoi.routing.agent_daemon fleet-scout
advoi-agent-briefs    → python -m advoi.routing.agent_daemon brief-curator
advoi-agent-review    → python -m advoi.routing.agent_daemon review-queue
advoi-agent-systems   → python -m advoi.routing.agent_daemon systems-pulse
advoi-agent-memory    → python -m advoi.routing.agent_daemon memory-scout
advoi-agent-guardian  → python -m advoi.routing.agent_daemon guardian-sentinel
```

Default interval: `ADVOI_AGENT_INTERVAL_SECS=45` in `deploy/.env.staging.example`.

### Local supervisor (development)

Single process runs all six (`DEFAULT_AGENT_IDS = tuple(AGENTS.keys())`):

```bash
uv run python -m advoi.routing.agent_supervisor
```

File: `advoi/routing/agent_supervisor.py`

### Run-six (API / platform)

- `POST /api/agents/run-six?refresh=true` — parallel refresh of all specialists.
- Optional `dispatch_squads=true` — platform path via `advoi/squads/orchestrate.run_six_with_platform`.
- Voice capabilities expose `run_six` / squads dispatch as operator actions.

## API integration

- `GET /api/agents` — Lists 6 agents; includes `last_run` when Redis is reachable; `ready` / `total` / `all_ready`.
- `GET /api/frames` — Lists 6 decision frames (A–F).
- `POST /api/frames/{frame_id}/run` — On-demand execution (bypasses cache when `refresh=true`).
- `POST /api/agents/run-six` — Parallel multi-agent refresh.
- PWA `VoiceSession.tsx` — Calls frame API, publishes `{type:"speak", text}` on LiveKit data channel.

## What is not built

| Capability | Status |
|------------|--------|
| Full free-speech NLU → frame | Keyword / intent routing only |
| Agent-to-agent handoff protocol | Not built (systems-pulse orchestrates in-process) |
| Per-user agent personalization | Not built |
| Agent health metrics / alerting | Logs + guardian events; no full alerting product |
| Ontology-generated agent/frame manifests | Deferred (`advoi-ontology-registry-01`) |

## Testing

| Script / test | Purpose |
|---------------|---------|
| `scripts/agents-smoke-test.ps1` | Windows: all frames + agent registry |
| `scripts/agents-smoke-test.sh` | Bash: same (host that reaches API) |
| `scripts/voice-smoke-test.sh` | Full voice journey against public URL |
| `tests/test_frames.py` | Unit tests with mock frames |
| `tests/test_agent_supervisor.py` | Supervisor covers **all 6** agents (`len(DEFAULT_AGENT_IDS) == 6`) |
| `tests/test_run_all_agents.py` | `run-six` API alias + parallel refresh |
