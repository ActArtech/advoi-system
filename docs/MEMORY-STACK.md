# ADVoi Memory Stack

**ADR-026** — Hindsight (now) + Letta (v0.2 optional) + Postgres + Redis.

## Tier mapping

```
Voice / ADVoi routing
    │
    ├── Hindsight (via Hermes)     → portfolio facts, decisions, governance, synthesis
    │
    ├── Letta (self-hosted, v0.2)  → agent identity, user prefs, squad operational learning
    │
    ├── PostgreSQL (advoi)         → structured state: projects, briefs, master-state.json
    │
    └── Redis                      → ephemeral: last 3–5 turns + rolling summary
```

**Rule:** Hindsight = what the system knows and believes. Letta = who the agent is and how it improves. Postgres = canonical records. Guardian log = failures only.

## Phase 1 — Hindsight only (this week)

```bash
ssh deploy@187.77.140.216
bash /opt/advoi/scripts/memory-setup-hindsight.sh   # non-interactive; local embedded by default
# Or interactive: docker exec hermes hermes memory setup hindsight
```

`deploy/.env`:

```env
MEMORY_PROVIDER=hindsight
HERMES_CONTAINER=hermes
LETTA_ENABLED=false
```

Code path: `advoi/memory/router.py` → `hindsight.py` (`hindsight-client`, bridged via Hermes container for local mode).

## Phase 2 — Add Letta (optional)

1. Clone `/opt/letta` — see `docs/LETTA-OPTIONAL.md`
2. Set `LETTA_ENABLED=true`, `MEMORY_PROVIDER=both`
3. Never write the same event to Hindsight and Letta — use `write_targets.py`

## What NOT to store as memory

- Fleet backlog / task queue → operational queue, not recall
- Guardian stack traces → `guardian_log.py` only
- Cognee + SurrealDB + everything at once → pick this stack only

## Checklist before memory is "done"

- [ ] `bash scripts/memory-setup-hindsight.sh` on VPS (switches Hermes off holographic → hindsight)
- [ ] `bash scripts/memory-health.sh` passes bridge probe
- [ ] `MEMORY_PROVIDER=hindsight` in `/opt/advoi/deploy/.env`
- [ ] `advoi/memory/write_targets.py` — no duplicate writes for same event type
- [ ] Aether `.aether/DECISIONS.md` for architecture; Hindsight for synthesized insights
- [ ] Guardian errors in `docs/error-log/` — not in Hindsight
- [ ] ADR-026 recorded in `docs/decision-log/DECISION-LOG.md`
- [ ] (v0.2) Letta container + MemFS git backup

## Decision matrix

| Priority | Choose |
|----------|--------|
| Fastest, Hermes-native, governance | **Hindsight only** |
| Long-lived self-editing agent identity | **Letta only** |
| Full executive OS | **Hindsight + Letta + Postgres** ← recommended end state |