# memory/

Hybrid memory per **ADR-009** (three tiers) and **ADR-026** (Hindsight ± Letta).

## Write targets (no double-write)

| Store | What goes here | What does NOT |
|-------|----------------|---------------|
| **Hindsight** (via Hermes) | Portfolio facts, governance, cross-project synthesis, beliefs | Squad chatter, errors, ephemeral turns |
| **Letta** (optional v0.2) | Agent identity, user prefs, squad operational learning | Portfolio facts (→ Hindsight) |
| **Postgres** | Structured canonical: projects, decision briefs, master-state | Long-form synthesis (→ Hindsight) |
| **Redis** | Last 3–5 voice turns + rolling summary | Anything strategic |
| **Guardian log** | Runtime errors, recovery notes | Beliefs or preferences |

## Usage

```python
from advoi.memory import MemoryRouter, MemoryEventType

router = MemoryRouter()

# Before each turn
ctx = await router.recall(session_id="voice-abc", query=user_text)

# After turn
await router.retain(
    MemoryEventType.VOICE_TURN,
    {"role": "user", "text": user_text},
    session_id="voice-abc",
)
await router.retain(
    MemoryEventType.PORTFOLIO_FACT,
    {"summary": "Clapart promoted to active venture", "project": "clapart"},
)
```

## VPS setup (Hindsight — start here)

```bash
docker exec hermes hermes memory setup   # pick Hindsight
```

Env: `MEMORY_PROVIDER=hindsight`, `HERMES_CONTAINER=hermes`

## Letta (v0.2 — optional)

Separate clone at `/opt/letta` — see `docs/LETTA-OPTIONAL.md`.  
Set `LETTA_ENABLED=true` only when container is up.

## Files

| Module | Role |
|--------|------|
| `write_targets.py` | Event → store routing table |
| `router.py` | recall/retain orchestration |
| `hindsight.py` | Hermes CLI bridge |
| `letta.py` | Letta HTTP client (optional) |
| `postgres_store.py` | Structured events table |
| `redis_store.py` | Ephemeral window |
| `guardian_log.py` | Error log (not memory) |