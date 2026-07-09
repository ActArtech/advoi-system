# What we did — multi-agent platform sprint (2026-07-09 to 2026-07-10)

Chronological summary of development completed in this sprint.  
**Repo:** `advoi-system` @ `25af012`  
**Tests:** 190 pytest collected, all passing locally

---

## Executive summary

We went from a **3-frame voice demo** to a **6-agent executive control plane** with:

- Unified parallel orchestration (CLI, API, voice, PWA, dashboard)
- Operator voice commands (capabilities, run all, stop/restart daemons)
- Squad dispatch bridge (4 squads mapped to 6 agents)
- Platform diagnostics (memory, OTel readiness, multi-agent latency)
- Agent dashboard at `/dashboard`

**Staging still needs redeploy** to pick up this code (BUG-005).

---

## Commits (newest first)

| Commit | Summary |
|--------|---------|
| `25af012` | `six-squads` CLI mode + `run-six-agents.ps1` |
| `2c48b5b` | M3-M6: squads orchestrate, platform diagnostics, dashboard |
| `3ffcce5` | Tighter run-all spoken summary |
| `ae753b0` | Unified `run_all_specialist_frames` for CLI/API/voice |
| `402f8d3` | Voice stop/restart agent daemons + confirmation gate |
| `fe0d982` | Operator catalog, 6-frame PWA controls, meta voice intents |
| `dbd4c25` | Voice-local storage probe + server fallback |
| `5c5f36d` | Aether portfolio routing + lifecycle APIs |

---

## 1. Six specialist agents (Options A-F)

| Agent | Frame | Voice phrase |
|-------|-------|--------------|
| fleet-scout | fleet_status | fleet status |
| brief-curator | open_briefs | open briefs |
| review-queue | queue_deep_review | queue review (confirm) |
| systems-pulse | systems_pulse | systems pulse |
| memory-scout | memory_health | memory health |
| guardian-sentinel | guardian_status | guardian status |

**Docker:** 6 daemon services (`advoi-agent-fleet` through `advoi-agent-guardian`).

---

## 2. Multi-agent run modes

| Mode | Command |
|------|---------|
| CLI — 6 frames | `uv run advoi-orchestrate six --refresh` |
| CLI — 6 + squads | `uv run advoi-orchestrate six-squads --refresh` |
| CLI — JSON | `uv run advoi-orchestrate json --refresh` |
| One script | `.\scripts\run-six-agents.ps1 -Refresh` |
| Via API | `POST /api/agents/run-six?refresh=true` |
| 6 + squad dispatch | `POST /api/agents/run-six?dispatch_squads=true` |
| Background tickers | `uv run advoi-supervisor` (all 6 in one process) |
| Full local stack | `.\scripts\run-multi-agent-stack.ps1 -WithRedis` |

**Core module:** `advoi/routing/orchestrator.py` — `run_all_specialist_frames()`, condensed `spoken_summary`.

---

## 3. Operator control layer

Voice and PWA operators (no vague LLM fallback):

| Intent | Phrase | Action |
|--------|--------|--------|
| capabilities | what can you do | Lists 6 specialists + systems access |
| run_all | run all agents | Parallel 6-frame run |
| dispatch_squads | dispatch all squads | 6-frame run + 4 squad jobs |
| stop_agents | stop agents confirm | Pause daemons, clear cache |
| restart_agents | restart agents | Resume + prewarm |
| firstmate_info | do you use firstmate | Definitive fleet path answer |
| github_info | github access | advoi-system + fleet repo |

**API:** `GET /api/capabilities`  
**PWA buttons:** Run all 6, Dispatch squads, Systems pulse, Prewarm, What can you do, Stop/Restart agents

---

## 4. Agent daemon control

| Endpoint | Purpose |
|----------|---------|
| `GET /api/agents/control` | Pause state, Redis, Docker control flag |
| `POST /api/agents/stop` | Pause ticks (confirmation required) |
| `POST /api/agents/restart` | Resume + prewarm |

Redis pause flag with in-memory fallback for local dev without Redis.

---

## 5. Squad execution bridge (M5)

Four squads mapped to agents:

| Squad | Channel | Agents |
|-------|---------|--------|
| fleet-squad | firstmate | fleet-scout |
| briefs-squad | hermes | brief-curator |
| review-squad | advoi | review-queue |
| platform-squad | advoi | systems-pulse, memory-scout, guardian-sentinel |

| Endpoint | Purpose |
|----------|---------|
| `GET /api/squads` | Registry |
| `POST /api/squads/dispatch` | Single squad job |
| `POST /api/squads/dispatch-all` | All 4 squads |

Mock mode default (`ADVOI_SQUAD_MOCK=true`). Set `DISCORD_WEBHOOK_URL` for live dispatch.

Run-six retains orchestration summary to operational memory (JSONL or Letta when enabled).

---

## 6. Platform diagnostics (M4)

| Endpoint | Reports |
|----------|---------|
| `GET /api/diagnostics/platform` | Agents ready, Redis, Letta, OTel, squads |
| `GET /api/diagnostics/latency` | Includes `run_six_ms` (full 6-frame parallel timing) |

OTel wiring exists (`OTEL_ENABLED=true` + optional `[observability]` deps). Not enabled on VPS yet.

---

## 7. Dashboard (M6 MVP)

**Route:** `/dashboard`  
**Features:** Squad-grouped agent cards, warmth status, Run all 6, Dispatch squads, latency/SLA chips.

React Flow deferred; CSS grid graph ships first.

---

## 8. Aether portfolio (Phase 4.3)

| Endpoint | Purpose |
|----------|---------|
| `GET /api/aether/portfolio` | Venture list |
| `GET /api/aether/status` | Lifecycle + gate alignment |
| `GET /api/aether/gate` | Active venture gate |
| `GET /api/aether/routes` | Frame-to-venture routes |
| `POST /api/aether/reload` | Reload portfolio JSON |

CLI: `uv run advoi aether status`

---

## 9. API surface (complete catalog)

| Method | Path |
|--------|------|
| GET | `/api/health` |
| POST | `/api/livekit/token` |
| GET | `/api/session`, `/api/frames`, `/api/capabilities` |
| GET | `/api/agents`, `/api/agents/control` |
| POST | `/api/agents/prewarm`, `/api/agents/stop`, `/api/agents/restart` |
| POST | `/api/agents/orchestrate`, `/api/agents/run-all`, `/api/agents/run-six` |
| POST | `/api/frames/{id}/run` |
| POST | `/api/voice/intent`, `/api/voice/respond`, `/api/voice/speak` |
| GET | `/api/review-queue`, `/api/review-queue/{id}` |
| GET | `/api/squads` |
| POST | `/api/squads/dispatch`, `/api/squads/dispatch-all` |
| GET | `/api/aether/portfolio`, `/gate`, `/routes`, `/status`, `/ventures/{id}` |
| POST | `/api/aether/reload` |
| GET | `/api/diagnostics/agents`, `/guardian`, `/memory`, `/voice`, `/latency`, `/platform` |

---

## 10. Scripts reference

| Script | Purpose |
|--------|---------|
| `run-six-agents.ps1` | One-shot 6-agent run (CLI or API) |
| `run-multi-agent-stack.ps1` | API + supervisor + smoke |
| `orchestrate-agents.ps1` | CLI orchestrate wrapper |
| `orchestrate-6-once.ps1` | JSON export one-shot |
| `agents-smoke-test.ps1` | 6 frames + run-six + squads + platform |
| `staging-redeploy.sh` | VPS deploy (closes BUG-005) |

---

## 11. What is still open

| Priority | Gap |
|----------|-----|
| P0 | Staging redeploy — live site on old 3-frame build |
| P0 | Human voice E2E sign-off (15 min phone test) |
| P1 | Redis on local stack for agent cache warmth (`-WithRedis`) |
| P2 | `LETTA_ENABLED=true` on VPS |
| P2 | `OTEL_ENABLED=true` on VPS |
| P2 | Live squad webhooks (`ADVOI_SQUAD_MOCK=false`) |
| P3 | React Flow interactive dashboard |
| P3 | Playwright PWA smoke (no mic) |

---

## 12. Quick verify (local)

```powershell
cd D:\Down\livekit-agent\deployment\advoi\advoi-system
$env:ADVOI_FRAME_MOCK="true"
uv run pytest tests/ -q                           # 190 pass
.\scripts\run-six-agents.ps1 -Refresh             # CLI 6 agents
.\scripts\run-multi-agent-stack.ps1 -WithRedis    # API + supervisor + smoke
# Dashboard: http://localhost:3000/dashboard
```

---

## Related docs

- [SYSTEM-STATUS.md](SYSTEM-STATUS.md) — authoritative snapshot (updated 2026-07-10)
- [DEVELOPMENT-MILESTONES.md](DEVELOPMENT-MILESTONES.md) — prioritized roadmap
- [MANUAL-TEST-TRACKER.md](../operations/MANUAL-TEST-TRACKER.md) — human test matrix
- [DEV-LOG.md](../dev-log/DEV-LOG.md) — chronological dev log