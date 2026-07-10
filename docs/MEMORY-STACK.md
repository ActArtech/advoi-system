# ADVoi Memory Stack

**ADR-026** — Hindsight (strategic) + Postgres (canonical) + Redis (ephemeral) + optional Letta (v0.2).

## Tier mapping

```
Voice / ADVoi routing
    │
    ├── Hindsight (via Hermes)     → portfolio facts, decisions, governance, synthesis
    │       └── advoi-memory-bridge (HTTP :8095) — only service with docker.sock
    │
    ├── Letta (self-hosted, v0.2)  → agent identity, user prefs, squad operational learning
    │
    ├── PostgreSQL (advoi)         → decision_briefs, portfolio_events (PEL), memory_events (deprecated dual-write), master-state
    │
    └── Redis                      → ephemeral voice turns + advoi:briefs:open cache
```

**Rule:** Hindsight = what the system knows and believes. Postgres = canonical briefs/records. Redis = last 5 voice turns per session. Guardian log = failures only.

**PEL (runtime):** Moat R1 append-only control-plane log is `portfolio_events` via `advoi.analytics.pel.append_event`. Emit points: `run_frame` (`frame_run`), `invoke_fleet_trigger` / confirmation (`fleet_trigger`, `guardian_gate`), voice frame/operator intents (`voice_intent` — not every Redis turn). Schema: versioned migrations `deploy/migrations/000_baseline_tables.sql` then `001_portfolio_events.sql`, applied at API boot (`advoi.db.migrations`). **`memory_events` is not dropped yet** — `retain_structured` may still write legacy rows; see [migration-plan](../data/feedback-evidence/advoi-data-memory-events-pel-01/migration-plan.md). Design: [architecture/07-portfolio-event-log.md](architecture/07-portfolio-event-log.md). Ops: [operations/MIGRATIONS.md](operations/MIGRATIONS.md).

## Container architecture (production)

App containers (`advoi-api`, `advoi-voice`, agent daemons) **cannot** `docker exec` into Hermes.

| Path | Who uses it |
|------|-------------|
| `HINDSIGHT_BRIDGE_URL=http://advoi-memory-bridge:8095` | All app containers — recall/retain via HTTP |
| `docker exec hermes python hindsight-bridge.py` | `advoi-memory-bridge` only (docker.sock mounted) |
| Redis `advoi:briefs:open` | Brief Curator **cache only** (fill-on-read / invalidate-on-write) |
| Postgres `decision_briefs` | Brief Curator **canonical** path |

## `deploy/.env` (required)

```env
MEMORY_PROVIDER=hindsight
HERMES_CONTAINER=hermes
HINDSIGHT_MODE=local
HINDSIGHT_BRIDGE=hermes
HINDSIGHT_BRIDGE_URL=http://advoi-memory-bridge:8095
HINDSIGHT_BANK_ID=advoi-portfolio
LETTA_ENABLED=false
REDIS_URL=redis://redis:6379/0
DATABASE_URL=postgresql://advoi:***@postgres:5432/advoi
# Optional TTL / retention (defaults shown)
# ADVOI_REDIS_VOICE_TTL_SEC=3600
# ADVOI_REDIS_VOICE_MAX_TURNS=5
# ADVOI_MEMORY_EVENTS_RETENTION_DAYS=90
```

## TTL / compaction policy

Proportionate retention — ephemeral is short; legacy structured rows are age-pruned; PEL is **not** compacted by this policy.

| Store | Object | Compaction | Default | Env / code |
|-------|--------|------------|---------|------------|
| **Redis** | Voice turns `advoi:ephemeral:{session}` | Rolling list + key TTL on every retain | Max **5** turns; TTL **3600s** | `ADVOI_REDIS_VOICE_MAX_TURNS`, `ADVOI_REDIS_VOICE_TTL_SEC` · `redis_store.ephemeral_*` |
| **Postgres** | Legacy `memory_events` | Age prune by `created_at` | Keep **90** days (floor **7**) | `ADVOI_MEMORY_EVENTS_RETENTION_DAYS` · `postgres_store.prune_memory_events` |
| **Postgres** | `portfolio_events` (PEL) | **No automatic delete** | Append-only SoR | Out of scope for this job |
| **Postgres** | `decision_briefs`, `review_queue` | Lifecycle status, not age TTL | — | Product / frame paths |
| **Hindsight / Letta** | Beliefs / identity | Provider-managed | — | Not ADVoi compaction |

### Redis voice window

- On each `retain_ephemeral`, the list is `LPUSH` + `LTRIM` to max turns, then `EXPIRE` with the configured TTL.
- Idle sessions disappear after TTL; active sessions keep refreshing TTL on each turn.
- Invalid / missing env values fall back to defaults (never zero/negative TTL).

### `memory_events` retention job

Legacy mirror only — safe while PEL dual-write/soak is in progress. **Never** deletes `portfolio_events`.

```bash
# Dry-run (default): count rows older than retention window
bash scripts/memory-events-retention.sh
bash scripts/memory-events-retention.sh --dry-run

# Apply delete (explicit)
bash scripts/memory-events-retention.sh --apply
bash scripts/memory-events-retention.sh --apply --days 120

# Or: python scripts/memory-events-retention.py [--dry-run|--apply] [--days N]
```

Suggested weekly cron (after dry-run has been verified on the host):

```cron
20 3 * * 0 ENV_FILE=/opt/advoi/deploy/.env \
  bash /opt/advoi/scripts/memory-events-retention.sh --apply \
  >> /var/log/advoi-memory-events-retention.log 2>&1
```

**T0:** `uv run pytest tests/test_memory_ttl_retention.py -q`

## Setup on VPS

```bash
cd /opt/advoi
bash scripts/memory-setup-hindsight.sh      # once — Hermes embedded hindsight
bash scripts/ensure-deploy-secrets.sh       # sets HINDSIGHT_BRIDGE_URL
DEPLOY_MODE=staging bash scripts/vps-deploy.sh --profile app
bash scripts/seed-advoi-briefs.sh           # Postgres + Redis + Hindsight
bash scripts/memory-health.sh
```

## Voice loop (dynamic)

- **Recall** at session start — `MemoryRouter.recall()` in `advoi/voice/agent.py`
- **Retain** each turn — `VoiceMemoryProcessor` in pipeline → Redis (`VOICE_TURN`)
- **Briefs** — seed via `seed-advoi-briefs.sh` (PG canonical → Redis cache → optional Hindsight `portfolio_fact` enrich); Brief Curator does **not** triple-merge
- **PWA home list** — thin `GET /api/briefs` (PG→Redis only) feeds `PwaHomeBriefsSurface`; do not merge Hindsight into this endpoint

## Checklist

- [x] Hindsight setup on Hermes
- [x] `advoi-memory-bridge` service (HTTP → Hermes docker exec)
- [x] `HINDSIGHT_BRIDGE_URL` in deploy/.env
- [x] Voice turn retain to Redis
- [x] Postgres `decision_briefs` canonical + Redis cache + optional Hindsight enrich
- [x] `write_targets.py` — no duplicate writes per event type
- [x] Review queue Postgres persistence (`review_queue` table + enqueue/list/get/dequeue; survives API redeploy)
- [x] Thin `GET /api/briefs` for PWA home (no Hindsight on passive load)
- [x] Redis voice-turn TTL / max-turns env (`ADVOI_REDIS_VOICE_*`)
- [x] `memory_events` age retention job (`scripts/memory-events-retention.sh`, dry-run default)
- [ ] Shelve push for secrets (OPENAI key corruption on pull)
- [ ] (v0.2) Letta container

## What NOT to store as memory

- Fleet backlog / task queue → fleet snapshot files, not Hindsight
- Guardian stack traces → `guardian_log.py` only

## Cost optimization

Apply [HERMES-COST-OPTIMIZATION.md](HERMES-COST-OPTIMIZATION.md) on `/opt/hermes` before scaling voice recall frequency.