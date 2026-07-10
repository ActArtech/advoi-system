# Manual test tracker

**Purpose:** Record what humans still need to verify. **Does not block development** — agents continue Phase 4+ while items here stay open.

**Last updated:** 2026-07-10
**Staging:** https://advoi.keyteller.com  
**Local:** http://localhost:3000 (web) + http://127.0.0.1:8010 (API)

---

## How to use

| Column | Meaning |
|--------|---------|
| **Automated** | Covered by pytest or smoke scripts — no human needed |
| **Tested** | Human verified on a real device/browser (add date + tester) |
| **Not tested** | Built in code; awaiting human pass |
| **Bug** | Human test failed — log in [Known bugs](#known-bugs) |

Update this file when you test. Do not wait for full sign-off to ship code.

---

## Status summary

| Area | Automated | Tested | Not tested | Bugs |
|------|-----------|--------|------------|------|
| API + frames (4 agents) | Yes | Partial | Device voice | 0 |
| Path A — LiveKit PWA | Partial | No | Mic + TTS E2E | 1 open |
| Path B — Client voice | No | No | Kokoro/Parakeet load | 1 open |
| Path C — Server voice | Partial | No | Browser STT + API TTS | 0 |
| Review queue UI | Partial | No | Confirm on phone | 0 |
| Desktop briefs | Partial | No | `/briefs/[id]` click-through | 0 |
| Staging deploy | Yes | Partial | Post-deploy phone spot-check | 0 |

---

## Automated coverage (no human required)

These run in CI or via scripts. Re-run after every deploy.

| Check | Command | Last known |
|-------|---------|------------|
| Full pytest | `uv run pytest tests/ -q` | **190** passed |
| Agents smoke | `.\scripts\agents-smoke-test.ps1` | 6 agents + run-six + squads + platform |
| Run six script | `.\scripts\run-six-agents.ps1 -Refresh` | 6 frames CLI |
| Voice smoke | `.\scripts\voice-smoke-test.ps1` or `.sh` | Staging `ok: true` |
| Staging precheck | `.\scripts\staging-signoff-precheck.ps1` | Pass @ `c14c38d` |
| Web build | `cd web && npm run build` | Pass when no port contention |
| Latency SLA | `GET /api/diagnostics/latency` | `sla_ok: true` (~35ms API path) |

---

## Manual test matrix

### Path A — LiveKit PWA (`/`)

**Operator voice flows (after BUG-006/007 deploy):**

| Voice phrase | Expected |
|--------------|----------|
| what can you do | Lists 6 specialists + FirstMate/GitHub access |
| fleet status | Fleet Scout reads FirstMate backlog |
| systems pulse | Merged fleet + briefs + agent warmth |
| memory health / guardian status | Infrastructure frames D/E |
| run all agents | Parallel run-six summary |
| stop agents confirm | Pause daemons + clear cache (confirmation required) |
| restart agents | Resume ticks + prewarm all 6 |
| do you use firstmate | Read-only fleet path + active slug |
| do you have access to github | advoi-system + fleet github_repo |

**PWA operator buttons:** Run all 6 · Dispatch squads · Systems pulse · Prewarm · What can you do · Stop agents · Restart agents

**Dashboard (`/dashboard`):** Squad graph · Run all 6 · Dispatch squads · Platform metrics

| # | Test | Steps | Status | Tester / date |
|---|------|-------|--------|---------------|
| A1 | Connect voice | Open staging PWA, tap Connect, allow mic | **Not tested** | |
| A2 | Greeting TTS | Hear greeting within ~10s | **Not tested** | |
| A3 | Option A fleet | Tap frame → hear spoken summary | **Not tested** | |
| A4 | Option B briefs | Tap frame → hear brief list or empty | **Not tested** | |
| A5 | Option C review | Tap twice → confirm → hear queue message | **Not tested** | |
| A6 | Option D pulse | Tap or say "systems pulse" → hear merged summary | **Not tested** | |
| A7 | Voice intent | Say "fleet status" → hear reply without tapping | **Not tested** | |
| A8 | Two-turn confirm | Say "queue review" then "yes" | **Not tested** | |
| A9 | Review queue panel | Pending items show in PWA | **Not tested** | |
| A10 | Agent freshness | `last_run` chips update after interval | **Automated** (API) | staging 2026-07-08 |
| A11 | UI state machine chip | Open `/` — chip shows **Idle**; Connect → **Connecting** → **Connected**; tap a frame → **Frame running**; frame with Guardian confirm (e.g. deep review) → **Confirm pending**; force LiveKit/token fail → **Error**. Labels: idle, connecting, connected, frame_running, confirm_pending, error. Screenshot: `web/e2e/artifacts/ui-state-chip.png` (Playwright stub `web/e2e/voice-session-state.spec.ts`). Unit: `tests/test_voice_session_state.py`. | **Not tested** (automated reducer) | |

### Path B — Client voice (`/voice-local`)

| # | Test | Steps | Status | Tester / date |
|---|------|-------|--------|---------------|
| B1 | Model load (desktop) | Page reaches Ready; WASM backend | **Not tested** | |
| B2 | Parakeet STT | Listen → speak → transcript appears | **Not tested** | |
| B3 | Kokoro TTS | Test voice button plays audio | **Not tested** | |
| B4 | Agent reply | Say "systems pulse" → API reply + TTS | **Not tested** | |
| B5 | Auto fallback | If Kokoro fails → switches to server TTS | **Not tested** | |
| B6 | Typed fallback | Type command when mic fails | **Automated** (code path) | |
| B7 | iOS Safari | WebGPU/WASM model load | **Not tested** | |

### Path C — Server voice (`/voice-server`)

| # | Test | Steps | Status | Tester / date |
|---|------|-------|--------|---------------|
| C1 | No WebGPU needed | Page loads without Kokoro/Parakeet download | **Not tested** | |
| C2 | Server TTS | Test voice → `POST /api/voice/speak` plays MP3 | **Not tested** | |
| C3 | Browser STT | Listen → Chrome speech → transcript | **Not tested** | |
| C4 | Multi-agent | "fleet status", "open briefs", "systems pulse" | **Not tested** | |
| C5 | Agents roster | Four specialists listed | **Automated** (API 4 agents) | |

### API and modules (curl / Postman)

| # | Test | Endpoint | Status |
|---|------|----------|--------|
| M1 | Health | `GET /api/health` | **Automated** |
| M2 | Agents | `GET /api/agents` (4 agents) | **Automated** |
| M3 | Orchestrate | `POST /api/agents/orchestrate` | **Automated** |
| M4 | Voice speak | `POST /api/voice/speak` | **Automated** |
| M5 | Voice respond | `POST /api/voice/respond` | **Automated** |
| M6 | Review queue | `GET /api/review-queue` | **Automated** |
| M7 | Memory bridge | diagnostics `memory_bridge_mode` | **Automated** (staging: hermes) |
| M8 | Desktop brief | `/briefs/0` or real queue id | **Not tested** |

### Staging / ops

| # | Test | Steps | Status |
|---|------|-------|--------|
| O1 | Deploy smoke | voice-smoke + agents-smoke after deploy | **Automated** |
| O2 | Voice container | `advoi-voice` not restart-looping | **Tested** 2026-07-08 |
| O3 | Traefik routes | `/api/health` 200 on storefront host | **Tested** 2026-07-08 |
| O4 | LLM keys survive deploy | sync script + voice diagnostics `llm_key: true` | **Tested** 2026-07-08 |

---

## Known bugs

Log failures here. Link to GitHub issue when filed.

| ID | Severity | Path | Symptom | Workaround | Status |
|----|----------|------|---------|------------|--------|
| BUG-001 | High | Path B `/voice-local` | WebGPU: "Failed to get GPU adapter" / no backend | Use `/voice-server` (server TTS, browser STT) | **Mitigated** — server path shipped |
| BUG-002 | High | Path A staging | User hears nothing when `advoi-voice` missing LLM key | `sync-llm-keys-from-clapart.sh` + recreate voice container | **Mitigated** |
| BUG-003 | Low | Local dev | Many parallel pytest/node processes slow or hang tests | Kill stray `python`/`node`; clear `pytest-of-artec` temp | **Open** (env) |
| BUG-004 | Low | Path B Windows | First Kokoro/Parakeet load ~200MB; console cache noise | Expected; use Path C if blocked | **Mitigated** — storage probe + fallback |
| BUG-005 | **High** | Path A PWA staging | Only 3 frame buttons (A-C); frames D-F + Aether 404 | `bash scripts/staging-redeploy.sh` after `git pull` | **Open** — deploy drift |
| BUG-006 | **High** | Path A voice | "What can you do" / FirstMate / GitHub → vague LLM "I don't know" | Operator intents + `/api/capabilities` (2026-07-09 fix) | **Fixed in code** — needs deploy |
| BUG-007 | Med | Path A PWA | No operator controls (run all, prewarm, capabilities) | Operator bar in `VoiceSession.tsx` (2026-07-09) | **Fixed in code** — needs deploy |

---

## What we are building next (not blocked by manual tests)

Development continues per [improvement-roadmap.md](../current-state/improvement-roadmap.md):

| Phase | Work | Status |
|-------|------|--------|
| 3.6 | Server voice path | **Done** |
| 4.0 | Request trace + guardian confirmation | **Done** |
| 4.1 | Letta operational memory (code) | **Done** — VPS enable open |
| 4.2 | Guardian error recovery + notifications | **Done** |
| 4.3 | Aether venture routing | **Done** — redeploy open |
| 4.4 | Squad dispatch bridge | **Done** (mock) — live webhook open |
| 4.5 | Dashboard MVP (`/dashboard`) | **Done** — React Flow open |
| 4.6 | 6-agent orchestration + operators | **Done** (2026-07-10) |

---

## Quick manual session (15 min)

When you have time, this minimum pass closes the highest-value gaps:

1. **Path C (fastest):** http://localhost:3000/voice-server → Test voice → type `systems pulse` → Send
2. **Path A (staging):** https://advoi.keyteller.com → Connect → Options A–D
3. Mark rows **Tested** above and copy results to [E2E-SIGNOFF.md](E2E-SIGNOFF.md) if Path A passes

---

## Related docs

- [E2E-SIGNOFF.md](E2E-SIGNOFF.md) — formal Path A sign-off template
- [local-testing.md](local-testing.md) — dev environment setup
- [staging-runbook.md](staging-runbook.md) — deploy and recovery
- [gaps-and-blockers.md](../current-state/gaps-and-blockers.md) — priority gaps (P0 human E2E is informational, not a dev gate)