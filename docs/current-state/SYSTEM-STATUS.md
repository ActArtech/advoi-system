# ADVoi system status

**Authoritative snapshot** — what exists, what works, what is still open.  
**Updated:** 2026-07-10 (wave 4 wrap-up)  
**Repo:** `advoi-system` develop tip `61de279` (wave 4 Aether/arch; wrap-up branch may add docs tip)  
**Staging:** https://advoi-staging.keyteller.com @ `5d50805` — promote parked (SSH host key; GAP-013)

Manual testing does **not** block development. Track human checks in [MANUAL-TEST-TRACKER.md](../operations/MANUAL-TEST-TRACKER.md).

Sprint summary: [WHAT-WE-DID-2026-07-10.md](WHAT-WE-DID-2026-07-10.md)  
Milestones: [DEVELOPMENT-MILESTONES.md](DEVELOPMENT-MILESTONES.md)

---

## Executive summary

| Dimension | Status |
|-----------|--------|
| **Code (Build 1.5+)** | 6-agent plane + PWA shell + Aether Queued + Guardian write-path hard-gate (ADR-028) |
| **Automated tests** | **494** pytest collected (wave4 aether/write-path + PWA/PEL suites) |
| **Staging** | Bootstrap healthy @ `5d50805`; **promote parked** (SSH; develop `61de279`) |
| **Human voice E2E** | Not recorded (A11–A17 open) |
| **Phase 4** | Aether feed/publish/export T0; Guardian hard-gate T0; Letta/OTel VPS enablement open |

---

## Six specialist agents (A-F)

| Agent | Frame | Role |
|-------|-------|------|
| fleet-scout | fleet_status | FirstMate / Hermes fleet read |
| brief-curator | open_briefs | Open decision briefs |
| review-queue | queue_deep_review | Deep review queue (confirm) |
| systems-pulse | systems_pulse | Merged fleet + briefs pulse |
| memory-scout | memory_health | Memory stack probe |
| guardian-sentinel | guardian_status | Guardian policy + events |

### Run modes

| Mode | Command |
|------|---------|
| One-shot CLI | `uv run advoi-orchestrate six --refresh` |
| 6 + squads CLI | `uv run advoi-orchestrate six-squads --refresh` |
| Unified script | `.\scripts\run-six-agents.ps1 -Refresh` |
| API | `POST /api/agents/run-six?refresh=true` |
| API + squads | `POST /api/agents/run-six?dispatch_squads=true` |
| Supervisor | `uv run advoi-supervisor` |
| Docker | 6 `advoi-agent-*` services |
| Full stack | `.\scripts\run-multi-agent-stack.ps1 -WithRedis` |

---

## Voice paths

| Path | Route | Status |
|------|-------|--------|
| A LiveKit PWA | `/` | Built |
| B Client voice | `/voice-local` | Built (storage probe + server fallback) |
| C Server voice | `/voice-server` | Built |

---

## Operator commands (voice + PWA)

| Phrase / button | Action |
|-----------------|--------|
| what can you do | Capabilities catalog |
| run all agents | Parallel 6-frame run |
| dispatch all squads | 6 frames + 4 squad jobs |
| stop agents confirm | Pause daemons |
| restart agents | Resume + prewarm |
| do you use firstmate / github access | Definitive system answers |

PWA operator bar + `/dashboard` for visual multi-agent control.

---

## API surface (30+ routes)

Core: health, session, frames, capabilities, agents, prewarm, stop, restart, orchestrate, run-six, voice intent/respond/speak, review queue.

**Home thin reads:** `GET /api/briefs` (open decision briefs — Brief Curator PG→Redis only; read-only, no frame run / PEL); `GET /api/review-queue` (+ `/{id}`).

Squads: `GET /api/squads`, `POST /api/squads/dispatch`, `POST /api/squads/dispatch-all`.

Aether: portfolio, gate, routes, status, reload, ventures.

Diagnostics: agents, guardian, memory, voice, latency (incl. `run_six_ms`), platform.

Analytics: `POST /api/events` (PWA thin beacon → PEL).

---

## Frontend routes

| Route | Purpose |
|-------|---------|
| `/` | Home: `PwaHomeOnboarding` + `PwaHomeBriefsSurface` (open briefs + review queue cards) + LiveKit `VoiceSession` (6 frames + operators + chips) |
| `/dashboard` | Squad/agent graph, run 6, dispatch squads, Aether gate metric |
| `/voice-server` | Server STT + API TTS |
| `/voice-local` | Client WASM voice |
| `/briefs/[id]` | Desktop review follow-up |

---

## Automation gates

| Gate | Command |
|------|---------|
| Unit tests | `uv run pytest tests/ -q` (415 collected) |
| Multi-agent smoke | `.\scripts\agents-smoke-test.ps1` |
| Run six | `.\scripts\run-six-agents.ps1 -Api -Refresh` |
| Full stack | `.\scripts\run-multi-agent-stack.ps1 -WithRedis` |
| CI | `.github/workflows/advoi-ci.yml` |

---

## Gaps (prioritized)

### P0

| Gap | Action |
|-----|--------|
| Staging deploy drift | `bash scripts/staging-redeploy.sh` |
| Human E2E | [E2E-SIGNOFF.md](../operations/E2E-SIGNOFF.md) |

### P1

| Gap | Notes |
|-----|-------|
| Two-turn confirm on device | Code wired |
| Path B iOS WebGPU | Use Path C fallback |
| Redis warmth locally | Use `-WithRedis` on stack script |

### P2

| Gap | Notes |
|-----|-------|
| Letta on VPS | Code done; `LETTA_ENABLED=false` |
| OTel on VPS | `OTEL_ENABLED=false` |
| Live squad webhooks | `ADVOI_SQUAD_MOCK=true` default |
| React Flow dashboard | CSS MVP at `/dashboard` |

---

## Quick commands

```powershell
cd D:\Down\livekit-agent\deployment\advoi\advoi-system
$env:ADVOI_FRAME_MOCK="true"

uv run pytest tests/ -q
.\scripts\run-six-agents.ps1 -Refresh -DispatchSquads
.\scripts\run-multi-agent-stack.ps1 -WithRedis
# Dashboard: http://localhost:3000/dashboard
```

---

## Related docs

| Doc | Purpose |
|-----|---------|
| [WHAT-WE-DID-2026-07-10.md](WHAT-WE-DID-2026-07-10.md) | Sprint changelog |
| [DEVELOPMENT-MILESTONES.md](DEVELOPMENT-MILESTONES.md) | Prioritized milestones |
| [what-we-have.md](what-we-have.md) | Module inventory |
| [gaps-and-blockers.md](gaps-and-blockers.md) | Blockers |
| [improvement-roadmap.md](improvement-roadmap.md) | Phase plan |