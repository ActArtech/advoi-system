# Hermes Cost Optimization — ADVoi Context

**Canonical directive:** [`deployment/hermes/HERMES-COST-OPTIMIZATION.md`](../../../hermes/HERMES-COST-OPTIMIZATION.md)

ADVoi depends on Hermes for Hindsight memory and portfolio coordination. Apply the portfolio-wide directive there first; use this page for **ADVoi-specific** cost notes.

---

## Why this matters for ADVoi

| Path | Cost risk |
|------|-----------|
| Hermes Hindsight bridge | Recall before every voice turn loads memory context |
| `fm-bridge.sh` fleet triggers | Sub-agent or tool loops if unbounded |
| Paperclip / Discord side paths | Auxiliary work on main model |
| Long voice sessions | Context compression defaults may carry too much |

Stage 1 success does **not** require expensive Hermes loops — voice uses OpenAI via Pipecat directly; Hermes is memory + optional fleet bridge.

---

## ADVoi-relevant settings (priority)

### 1. Model & routing

- Keep Hermes **auxiliary** and **sub-agent** models on cheap tiers (see canonical doc §1).
- Do not route ADVoi memory setup (`hermes memory setup`) through high-cost thinking modes.

### 2. Context & memory

- Trim `/opt/hermes/data/memory/` and agent files regularly — affects Hindsight bridge token load.
- `MEMORY_PROVIDER=hindsight` in ADVoi `deploy/.env` — see [MEMORY-STACK.md](./MEMORY-STACK.md).
- Automemory: **ON** if Discord/team shares Hermes context; **OFF** if solo cost minimization.

### 3. Tools & MCP

- Disable code execution on Hermes profiles that only serve ADVoi memory bridge.
- Disconnect MCP servers not used by active portfolio ventures.
- `tool_search: auto` — avoid loading full tool surface every turn.

### 4. Hard limits

- Cap `max_turns` on any cron that touches fleet or Aether proactive cycles.
- `hard_stop: true` — prevents stuck agent spend while ADVoi voice is in testing.

### 5. Monitoring

- After ADVoi deploy, run `hermes insights` and compare 30-day tool/session patterns.
- On bridge errors: `undo` + corrective prompt — do not repeat failed `fm-bridge` messages.

---

## Coexistence on VPS

| Path | Role | Cost note |
|------|------|-----------|
| `/opt/hermes` | Memory + Discord | Apply full optimization directive |
| `/opt/advoi` | Voice PWA (OpenAI direct) | LiveKit + OpenAI keys in `deploy/.env` — separate from Hermes model bill |
| `/opt/firstmate-fleet` | Execution | Read-only from ADVoi; fleet has its own model config |

---

## Checklist (ADVoi operator)

- [ ] Canonical [HERMES-COST-OPTIMIZATION.md](../../../hermes/HERMES-COST-OPTIMIZATION.md) applied on VPS
- [ ] Hindsight memory files trimmed
- [ ] Unused Hermes skills/MCP disabled
- [ ] Cron jobs have explicit `max_turns`
- [ ] `bash scripts/memory-health.sh` passes without oversized recall payloads

---

See also [PLAN-SETUP-REVIEW.md](./PLAN-SETUP-REVIEW.md) for Stage 1 deploy blockers.