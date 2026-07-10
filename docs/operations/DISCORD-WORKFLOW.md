# Discord / FirstMate reply workflow

**Purpose:** Operator contract for the Discord crew channel that sits between ADVoi (voice/PWA) and FirstMate fleet execution.  
**Roadmap:** M8.4 (docs gate) · related M5.4–M5.6 (live webhook + ACK in fleet read) · moat R7  
**Status:** Documented as-implemented plus the ACK/PROMOTE/NEXT reply contract for live crew. Live webhook flip on staging remains open (M5.4–M5.5).

Related: [ROADMAP-VALIDATION.md](ROADMAP-VALIDATION.md) · [staging-runbook.md](staging-runbook.md) · [../architecture/08-system-logic-flows.md](../architecture/08-system-logic-flows.md) · [../../advoi/squads/README.md](../../advoi/squads/README.md) · [../PORTFOLIO-INTEGRATION.md](../PORTFOLIO-INTEGRATION.md)

---

## Roles

| Actor | Where | Role |
|-------|--------|------|
| **Operator** | ADVoi PWA / voice | Triggers fleet actions and squad dispatch after Guardian confirm |
| **ADVoi** | `advoi-api` + `advoi/fleet` + `advoi/squads` | Guardian gate, `fm-bridge` shell, optional Discord webhook POST |
| **Hermes** | Discord gateway container | Interactive AI + Discord bot presence (portfolio stack) |
| **FirstMate** | `/opt/firstmate-fleet` | Captain + crew loop; backlog, arm/stop/work verbs |
| **Crew** | Discord channel(s) | Human/agent workers who **ACK**, **PROMOTE**, or **NEXT** work items |

ADVoi does **not** replace Discord chat. It summarizes, confirms, and triggers; crew feedback still lands in Discord (and eventually fleet snapshot — M5.6).

---

## Bot setup

1. **Hermes Discord gateway** runs outside the ADVoi compose project (see [PORTFOLIO-INTEGRATION.md](../PORTFOLIO-INTEGRATION.md)). Do not overwrite Hermes or FirstMate trees when deploying ADVoi.
2. Create or reuse a Discord **bot application** with access to the FirstMate / crew channel used by the fleet.
3. Set on ADVoi (and staging env when going live):
   - `DISCORD_BOT_TOKEN` — bot token (Hermes/gateway may own the live bot; ADVoi keeps the same vars for squad bridge)
   - `FIRSTMATE_CHANNEL_ID` — snowflake of the crew channel operators watch
   - `DISCORD_WEBHOOK_URL` — incoming webhook URL for that channel (squad dispatch path)
4. Confirm the fleet tree is mounted read-only for snapshot and bridge-resolvable for triggers:
   - Host: `FIRSTMATE_FLEET_PATH=/opt/firstmate-fleet`
   - Trigger: `FIRSTMATE_TRIGGER_SCRIPT` or default `…/scripts/fm-hermes-trigger.sh`
   - ADVoi wrapper: `ADVOI_FM_BRIDGE_SCRIPT` → `scripts/fm-bridge.sh`
5. Keep `ADVOI_CONFIRMATION_REQUIRED=true` in production so high-risk fleet actions never shell without confirm.

**Smoke (no side effect beyond status):**

```bash
bash scripts/fm-bridge.sh "fleet status"
```

---

## Two outbound paths

### A — Fleet bridge (voice / PWA high-risk actions)

Used for structured actions: `wake_firstmate`, `start_development`, `run_next_backlog`, `fleet_stop`.

```text
Operator (voice/PWA)
  → Guardian evaluate_fleet_confirmation
  → advoi/fleet/trigger.py (invoke_fleet_trigger / fleet_trigger_from_voice)
  → scripts/fm-bridge.sh
  → fm-hermes-trigger.sh  (arm | stop | work <task>)
  → FirstMate fleet tree + Hermes/Discord crew loop
```

| Operator action | Bridge verb | Notes |
|-----------------|-------------|--------|
| `wake_firstmate` | `arm` | Arm fleet loop |
| `fleet_stop` | `stop` | Disarm / halt loop |
| `run_next_backlog` | `arm` + `work <task>` | Task from fleet backlog snapshot |
| `start_development` | `arm` + `work <task>` | Project-scoped kickoff |

Sole shell path: `advoi/fleet/trigger.py` → `resolve_fleet_exec` → `fm-bridge.sh` → `fm-hermes-trigger.sh`. Voice never shells the bridge directly. Optional 60s idempotency key on `POST /api/fleet/trigger` (`Idempotency-Key` / `idempotency_key`).

Mock: `ADVOI_FLEET_MOCK=true` skips shell (tests / dry-run).

### B — Squad webhook (dispatch crews)

Used for squad jobs (`advoi/squads/dispatch.py`) after confirmation where required (e.g. deep review squad).

```text
Confirmed intent
  → dispatch_squad_job(squad_id, action, …)
  → if ADVOI_SQUAD_MOCK: status=mock_queued (default)
  → else POST DISCORD_WEBHOOK_URL
       json: { "content": "[<Squad Name>] <action> (job <job_id>)" }
  → status=dispatched | webhook_failed
```

Default is **mock** (`ADVOI_SQUAD_MOCK=true`). Live traffic needs M5.4–M5.5:

1. Set `DISCORD_WEBHOOK_URL` on the VPS env file.
2. Set `ADVOI_SQUAD_MOCK=false` on staging only after operator confirm discipline is clear.
3. Dispatch-all / dashboard controls should post into the crew channel.

Payload is a plain Discord webhook `content` string today — not a custom JSON schema. Future parsers should key off `job_id` in the message.

---

## Reply workflow (ACK / PROMOTE / NEXT)

Crew (or FirstMate captain automation) replies in the FirstMate Discord channel. These tokens are the **closed-loop contract** for live squads and backlog items (moat R7). Use them as the first token or a clear line so humans and future fleet parsers agree.

| Reply | Meaning | When to use | ADVoi / fleet effect (target) |
|-------|---------|-------------|-------------------------------|
| **ACK** | Accepted; work started or queued by crew | After seeing a dispatch or `work <task>` | Crew status “in progress”; later visible in fleet read (M5.6) |
| **PROMOTE** | Promote branch / artifact / staging outcome | When implementation is ready for human promote or merge gate | Escalates to operator (not auto-merge from Discord alone) |
| **NEXT** | Current item done or blocked; pick next backlog | When crew finishes or cannot proceed | Captain/fleet runs next queued item; operator may re-trigger `run_next_backlog` |

### Operator discipline

1. **Dispatch only after Guardian confirm** for high-risk fleet actions.
2. **One active item per venture** when possible — avoid stacking dispatches before ACK.
3. Treat **PROMOTE** as a human gate: Discord is a signal, not a merge button. Staging promote remains operator-driven (see VPS / www promote scripts).
4. On **NEXT** with no queue: fleet status should show empty backlog; do not re-fire blindly.
5. If no ACK within a reasonable window (operator judgment; often ~15–30 min for small tasks), **escalate** (below) rather than re-dispatching the same job without checking Discord.

### Example thread

```text
[ADVoi webhook]  [Fleet Squad] dispatch (job fleet-squad-a1b2c3d4)
[crew]           ACK fleet-squad-a1b2c3d4 — picking up
…
[crew]           PROMOTE — branch fm/… ready for firstmate merge to develop
[operator]       merges / promotes on VPS; optional voice "fleet status"
…
[crew]           NEXT — item done, free for backlog
```

### Implementation note

- **Documented now (M8.4).** Automated “Discord crew ACK visible in fleet read” is still **M5.6** (T3). Until then, operators read ACK/PROMOTE/NEXT in Discord; fleet scout reads disk under `FIRSTMATE_FLEET_PATH`.
- Do not invent additional reply tokens without updating this doc and M5.6 parser plans.

---

## Escalation path

Ordered from least to most severe:

| Level | Trigger | Action |
|-------|---------|--------|
| **L0 Self** | Transient webhook failure, mock still on | Check `ADVOI_SQUAD_MOCK`, `DISCORD_WEBHOOK_URL`, API logs; re-dispatch once |
| **L1 Channel** | No ACK / silent crew | Ping FirstMate channel; restate job_id; ask ACK or NEXT |
| **L2 Guardian / stop** | Runaway or wrong work | Voice/PWA `fleet_stop` (confirm required) → bridge `stop` |
| **L3 Operator** | PROMOTE blocked, merge/SSH/host issues | Human: git promote, VPS runbooks, [gaps-and-blockers.md](../current-state/gaps-and-blockers.md) |
| **L4 Security** | Unauthorized access, token leak | Rotate `DISCORD_BOT_TOKEN` / webhook; revoke channel webhook; see error-log GP-012 class |

Guardian always sits **before** side effects. Confirmation denials do not shell `fm-bridge` and should not post webhooks for gated paths.

---

## Environment variables

| Variable | Path | Purpose | Default / note |
|----------|------|---------|----------------|
| `DISCORD_BOT_TOKEN` | Squad / Hermes | Bot auth | Empty in examples |
| `DISCORD_WEBHOOK_URL` | Squad dispatch | Incoming webhook POST | Empty → no live post |
| `FIRSTMATE_CHANNEL_ID` | Ops / gateway | Crew channel snowflake | Empty in examples |
| `ADVOI_SQUAD_MOCK` | Squads | `true` → mock_queued, no HTTP | **`true`** (safe default) |
| `ADVOI_FLEET_MOCK` | Fleet trigger | Skip shell | `false` |
| `ADVOI_CONFIRMATION_REQUIRED` | Guardian | Gate high-risk fleet + frames | **`true`** |
| `FIRSTMATE_FLEET_PATH` | Fleet read | Disk snapshot root | `/opt/firstmate-fleet` |
| `FIRSTMATE_TRIGGER_SCRIPT` | Bridge | Override `fm-hermes-trigger.sh` | Auto-detect under fleet/firstmate |
| `ADVOI_FM_BRIDGE_SCRIPT` | Bridge | Override `fm-bridge.sh` | `/app/scripts/fm-bridge.sh` in containers |
| `FM_HERMES_PROJECT` | Bridge env | Active project slug fallback | Often `clapart` / profile |
| `FIRSTMATE_CONTAINER` | Fleet host | Hermes/FirstMate container name | Host-specific |
| `ADVOI_FLEET_IDEMPOTENCY_WINDOW_SECS` | Fleet API | Dedupe window for trigger keys | `60` |

Sources: `.env.example`, `deploy/.env.staging.example`, `advoi/squads/dispatch.py`, `advoi/fleet/{bridge,trigger}.py`, `AGENTS.md`.

---

## Validation checklist (docs + ops)

| Step | How | Milestone |
|------|-----|-----------|
| Reply tokens documented | This file | **M8.4** |
| Bridge intents wired | T0 `tests/test_fleet_trigger.py` | M8.1 |
| Guardian on fleet | T0 `evaluate_fleet_confirmation` | M8.2 |
| Live webhook URL | Staging env + T2 dispatch | M5.4 |
| Mock off on staging | `ADVOI_SQUAD_MOCK=false` | M5.5 |
| ACK in fleet read | Human T3 + future parser | M5.6 |

---

## Cross-links

| Doc | Why |
|-----|-----|
| [ROADMAP-VALIDATION.md](ROADMAP-VALIDATION.md) § M5 / M8 | Status checkboxes |
| [08-system-logic-flows.md](../architecture/08-system-logic-flows.md) | Fleet bridge control-plane diagram |
| [advoi/squads/README.md](../../advoi/squads/README.md) | Squad vertical boundaries |
| [AGENTS.md](../../AGENTS.md) | Write-path rules for fm-bridge |
| [PORTFOLIO-INTEGRATION.md](../PORTFOLIO-INTEGRATION.md) | Hermes + firstmate-fleet layout on VPS |
| [reviews/PORTFOLIO-SYSTEM-MOAT.md](../reviews/PORTFOLIO-SYSTEM-MOAT.md) § R7 | ACK contract moat item |
