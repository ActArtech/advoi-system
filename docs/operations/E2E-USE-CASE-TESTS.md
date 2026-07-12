# End-to-end use case tests

**Purpose:** Human test playbook for full ADVoi journeys — portfolio context, voice, agents, briefs, and governance. Use this to validate staging before calling the system operational.

**Last updated:** 2026-07-11  
**Staging (current deploy):** https://advoi.keyteller.com  
**Canonical www staging:** https://advoi-staging.keyteller.com (promote path; may lag `/opt/advoi`)  
**Latest feature commit:** `541283d` (portfolio project selector + voice activation)

**Related docs:**
- [MANUAL-TEST-TRACKER.md](MANUAL-TEST-TRACKER.md) — row-level status (Tested / Not tested / Bug)
- [E2E-SIGNOFF.md](E2E-SIGNOFF.md) — formal Path A sign-off template
- [staging-runbook.md](staging-runbook.md) — deploy and smoke
- [../architecture/08-system-logic-flows.md](../architecture/08-system-logic-flows.md) — five backend flows

---

## How to use this document

1. Run **automated pre-checks** (below) after every deploy.
2. Pick a **session** (15–45 min) or run all **use cases** in order.
3. For each use case: follow steps, check pass criteria, record result in the tracker.
4. On failure: log bug ID in MANUAL-TEST-TRACKER, note recovery steps at bottom.

| Result | Meaning |
|--------|---------|
| **PASS** | All pass criteria met on real device/browser |
| **PARTIAL** | Core path works; minor UX or latency issues |
| **FAIL** | Blocker — log bug, do not mark operational |
| **SKIP** | Not in scope this run (e.g. Path B only) |

**Tester:** _______________ **Date:** _______________ **Device:** _______________ **Deploy ref:** _______________

---

## Automated pre-checks (run first)

Do not start human E2E until these pass.

```bash
# VPS or local against staging URL
ADVOI_BASE_URL=https://advoi.keyteller.com bash scripts/t2-staging-smoke.sh
ADVOI_BASE_URL=https://advoi.keyteller.com bash scripts/staging-signoff-precheck.sh
```

**Windows:**

```powershell
$env:ADVOI_BASE_URL = "https://advoi.keyteller.com"
.\scripts\staging-signoff-precheck.ps1
.\scripts\agents-smoke-test.ps1
```

| Check | Endpoint / command | Expected |
|-------|-------------------|----------|
| Health | `GET /api/health` | `agents_ready: 6`, `stage: voice-pwa-2` |
| Frames | `GET /api/frames` | 6 frames (A–F) |
| Voice diag | `GET /api/diagnostics/voice` | `ok: true`, LLM + LiveKit configured |
| Aether | `GET /api/aether/status` | `gate_verdict: pass` |
| Projects | `GET /api/portfolio/projects` | 4 ventures, each with `functions[]` |
| Pytest (local) | `uv run pytest tests/ -q` | All pass (~726 tests) |
| Web build (local) | `cd web && npm run build` | Exit 0 |

| Pre-check | Pass | Notes |
|-----------|------|-------|
| T2 smoke | [ ] | |
| Signoff precheck | [ ] | |
| Portfolio API 200 | [ ] | Was 404 before `541283d` |
| Latency SLA | [ ] | `GET /api/diagnostics/latency` → `sla_ok` (optional gate) |

---

## Session map (pick one or chain)

| Session | Time | Use cases | Best for |
|---------|------|-----------|----------|
| **S1 Morning captain** | 15 min | UC-01, UC-02, UC-03 | Daily executive loop |
| **S2 Voice operator** | 20 min | UC-04, UC-05, UC-06 | Meta commands + confirm |
| **S3 Agents power user** | 25 min | UC-07, UC-08, UC-09 | Slice orchestration |
| **S4 Portfolio governance** | 15 min | UC-10, UC-11, UC-12 | Aether + project context |
| **S5 Resilience** | 15 min | UC-13, UC-14 | Errors and fallbacks |
| **S6 Path C only** | 10 min | UC-15 | Fastest voice proof (no LiveKit) |
| **Full sign-off** | ~90 min | UC-01 through UC-15 | Release gate |

---

## UC-01: Open PWA and orient

**Actor:** Executive on phone or desktop  
**Goal:** Land on a healthy shell with project context and tabs.

### Steps

1. Open https://advoi.keyteller.com
2. Hard refresh (`Ctrl+Shift+R` or clear site data on mobile)
3. Confirm **project bar** at top (folder icon + venture name)
4. Confirm bottom nav: Voice | Agents | Briefs | More
5. Scroll Voice tab — see Connect, frame buttons A–F, home briefs surface

### Pass criteria

- [ ] Project bar visible and shows active venture (default often `gem-dev-shop` from gate)
- [ ] Six frame buttons visible (not three)
- [ ] No persistent error banner on load
- [ ] Home shows briefs/review section (`pwa-home-briefs-surface` or equivalent)

### Record

| Result | Date | Tester | Notes |
|--------|------|--------|-------|
| [ ] PASS / PARTIAL / FAIL | | | |

---

## UC-02: Select project via UI

**Actor:** Executive  
**Goal:** Switch active venture and scope downstream UI.

### Steps

1. Tap **project bar** to open dropdown
2. Select **ADVoi System** (`advoi-system`)
3. Confirm label updates to "ADVoi System"
4. Expand active project — tap function chip **Fleet status**
5. Select **Gem Dev Shop** — confirm label changes
6. Refresh page — confirm last selection persists (localStorage)

### Pass criteria

- [ ] Dropdown lists 4 ventures with slugs
- [ ] Active venture shows function chips (frames + bets)
- [ ] Selecting venture updates bar label without crash
- [ ] Function chip shows combined label (e.g. `ADVoi System · Fleet status`)
- [ ] Selection survives refresh

### API mirror (optional)

```bash
curl -X POST https://advoi.keyteller.com/api/portfolio/active \
  -H "Content-Type: application/json" \
  -d '{"venture_id":"advoi-system","function_id":"fleet_status"}'
```

### Record

| Result | Date | Tester | Notes |
|--------|------|--------|-------|
| [ ] PASS / PARTIAL / FAIL | | | |

---

## UC-03: Morning pulse (tap + voice)

**Actor:** Executive starting the day  
**Goal:** One-tap or one-phrase operational snapshot.

### Steps

1. Project: **ADVoi System** (or gate-active venture)
2. Tap **60s morning pulse** CTA (if shown) or **Option D** (systems pulse)
3. Wait for TTS / status text
4. Connect voice (Path A) if not connected
5. Say: **"systems pulse"**
6. Check status chips: UI state, SLA, Aether gate

### Pass criteria

- [ ] Tap path returns spoken summary (fleet + briefs + agent warmth)
- [ ] Voice path returns same class of summary
- [ ] Aether gate chip shows verdict (pass/hold/fail)
- [ ] No silent failure after 15s

### Record

| Result | Date | Tester | Notes |
|--------|------|--------|-------|
| [ ] PASS / PARTIAL / FAIL | | | |

---

## UC-04: Voice connect and greet (Path A)

**Actor:** Executive on phone  
**Goal:** LiveKit session + server TTS greeting.

### Steps

1. Voice tab → **Connect voice**
2. Allow microphone when prompted
3. Wait for greeting within ~10s
4. Confirm connection indicator (green / connected state)

### Pass criteria

- [ ] Mic permission flow works (or clear error if denied — see UC-13)
- [ ] Hear ADVoi greeting
- [ ] PWA stays connected; no immediate disconnect loop

### Record

| Result | Date | Tester | Notes |
|--------|------|--------|-------|
| [ ] PASS / PARTIAL / FAIL | | | |

---

## UC-05: Run all six frames by voice

**Actor:** Executive  
**Goal:** Each specialist frame responds with distinct spoken summary.

### Steps

Say each phrase (or tap equivalent button):

| # | Say | Specialist |
|---|-----|------------|
| A | "fleet status" | Fleet Scout |
| B | "open briefs" | Brief Curator |
| C | "queue deep review" | Review Queue |
| D | "systems pulse" | Systems Pulse |
| E | "memory health" | Memory Scout |
| F | "guardian status" | Guardian |

### Pass criteria

- [ ] All six return non-empty spoken summaries
- [ ] No generic "I don't know" for operator-class phrases
- [ ] Status area updates after each run

### Record

| Result | Date | Tester | Notes |
|--------|------|--------|-------|
| [ ] PASS / PARTIAL / FAIL | | | |

---

## UC-06: Voice project switch and scoped frame

**Actor:** Executive  
**Goal:** Voice changes active project and can run a frame in context.

### Steps

1. Say: **"switch to advoi"** (or "switch to advoi system")
2. Confirm project bar updates to ADVoi System
3. Say: **"fleet status on advoi"** (activate project + frame)
4. Confirm fleet summary references advoi context

### Pass criteria

- [ ] `switch_project` updates UI project bar
- [ ] Spoken acknowledgment (not silent)
- [ ] `activate_function` runs frame after switch
- [ ] Agents tab (if opened) scopes to selected venture squads/frames

### Record

| Result | Date | Tester | Notes |
|--------|------|--------|-------|
| [ ] PASS / PARTIAL / FAIL | | | |

---

## UC-07: Voice meta operators

**Actor:** Power user  
**Goal:** Non-frame commands route correctly.

### Steps

| Say | Expected behavior |
|-----|-------------------|
| "what can you do" | Lists capabilities / six specialists |
| "run all agents" | Parallel six-frame style summary |
| "github status" | Repo/CI style summary (if configured) |
| "queue deep review" then "yes" | Two-turn confirm; queue message |

### Pass criteria

- [ ] Capabilities response mentions fleet/GitHub/agents
- [ ] Confirm flow shows Guardian copy before destructive/write actions
- [ ] "yes" after confirm executes pending action

### Record

| Result | Date | Tester | Notes |
|--------|------|--------|-------|
| [ ] PASS / PARTIAL / FAIL | | | |

---

## UC-08: Agents tab — preset and single slice

**Actor:** Operator  
**Goal:** Run orchestration from Agents tab with project scope.

### Prerequisites

- Active project set (UC-02)
- Agents tab open

### Steps

1. Confirm squad tiles match active venture (not all squads if scoped)
2. Run **Morning pulse** quick pick or preset
3. Run single agent slice (e.g. Fleet status tile)
4. Watch status line and result card

### Pass criteria

- [ ] At least one preset completes with spoken_summary or status OK
- [ ] Scoped squads/frames align with active venture
- [ ] No duplicate API calls when same frame run from Voice (voice mirror — UC-09)

### Record

| Result | Date | Tester | Notes |
|--------|------|--------|-------|
| [ ] PASS / PARTIAL / FAIL | | | |

---

## UC-09: Agents — chain, queue, and voice mirror

**Actor:** Power operator  
**Goal:** Advanced orchestration and cross-tab sync.

### Steps

1. **Chain:** Run preset chain (e.g. morning → ops)
2. **Queue:** Enqueue 2 slices; toggle auto-run; run queue (button or **Y** on desktop)
3. **Follow-up banner:** After a run, accept suggested follow-up if shown
4. **Voice mirror:** From Voice tab, run "fleet status"; switch to Agents — status should reflect run without manual refresh lag

### Pass criteria

- [ ] Chain runs slices in order (or queue order)
- [ ] Queue drains without stuck "running" state
- [ ] Voice-initiated frame appears in Agents orchestration state
- [ ] Keyboard shortcuts work on desktop (C / Shift+C / S / Y) — optional

### Record

| Result | Date | Tester | Notes |
|--------|------|--------|-------|
| [ ] PASS / PARTIAL / FAIL | | | |

---

## UC-10: Add custom project feature

**Actor:** Venture lead  
**Goal:** Track a new function label under active project.

### Steps

1. Open project dropdown with **Gem Dev Shop** active
2. In "Add feature" input, type: `Voice onboarding v2`
3. Tap **Add**
4. Confirm chip appears under active project
5. Refresh — chip still present

### Pass criteria

- [ ] Custom feature persists in localStorage after refresh
- [ ] Selecting custom chip sets active function label
- [ ] No server error (custom features are client-side today)

### Record

| Result | Date | Tester | Notes |
|--------|------|--------|-------|
| [ ] PASS / PARTIAL / FAIL | | | |

---

## UC-11: Home briefs and review queue (A17)

**Actor:** Executive  
**Goal:** Briefs and review work without leaving home Voice tab.

### Steps

1. On `/` Voice tab, scroll to **Open briefs** / **Review queue**
2. Confirm brief cards load (or empty state)
3. Tap **Hear open briefs** or run Option B
4. Run Option C twice — confirm Guardian flow
5. Confirm review list updates after queue

### Pass criteria

- [ ] Briefs surface visible on home (not only `/briefs`)
- [ ] Review queue shows pending items or clear empty state
- [ ] Confirm on C matches voice/tap parity (same Guardian copy)
- [ ] `advoi:briefs-refresh` updates list after frame (no stale cards)

### Record

| Result | Date | Tester | Notes |
|--------|------|--------|-------|
| [ ] PASS / PARTIAL / FAIL | | | |

---

## UC-12: Aether gate and dashboard

**Actor:** Portfolio operator  
**Goal:** Governance context visible and consistent.

### Steps

1. Note Aether chip on Voice tab after any frame run
2. Open `/dashboard` — gate metric, squad graph, run-six
3. Compare:
   - `GET /api/aether/status` → `active_slug`, `gate_verdict`
   - Project bar active venture
   - Frame result `gate_active_slug` in network tab (optional)

### Pass criteria

- [ ] Gate verdict visible in UI
- [ ] Dashboard loads without 500
- [ ] Active venture story is coherent (gate vs selector vs fleet slug documented if mismatched)

### Record

| Result | Date | Tester | Notes |
|--------|------|--------|-------|
| [ ] PASS / PARTIAL / FAIL | | | |

---

## UC-13: Error and permission paths

**Actor:** Any user  
**Goal:** Failures are recoverable.

### Steps

| Scenario | Action |
|----------|--------|
| Mic denied | Deny mic → see error panel → retry after allow |
| API slow | Throttle network (optional) → SLA chip shows err, app stable |
| Voice container down | Use Path C fallback link |

### Pass criteria

- [ ] Mic deny shows actionable message (A13)
- [ ] App does not white-screen on API errors
- [ ] Fallback link to `/voice-server` works

### Record

| Result | Date | Tester | Notes |
|--------|------|--------|-------|
| [ ] PASS / PARTIAL / FAIL | | | |

---

## UC-14: Briefs tab and deep link

**Actor:** Desktop user  
**Goal:** Navigate briefs outside Voice home surface.

### Steps

1. Bottom nav → **Briefs**
2. Open a brief card → `/briefs/[id]` or external `brief_url`
3. Return to Voice — context preserved

### Pass criteria

- [ ] Briefs tab loads list
- [ ] At least one brief opens readable detail
- [ ] Back navigation returns to shell

### Record

| Result | Date | Tester | Notes |
|--------|------|--------|-------|
| [ ] PASS / PARTIAL / FAIL | | | |

---

## UC-15: Path C server voice (no LiveKit)

**Actor:** Tester needing fast proof  
**Goal:** Voice loop without WebRTC.

### Steps

1. Open https://advoi.keyteller.com/voice-server
2. Tap test voice / allow mic per page instructions
3. Type or speak: `systems pulse`, `open briefs`, `switch to hermes`

### Pass criteria

- [ ] Server TTS plays or text reply shown
- [ ] Intents resolve without LiveKit connect
- [ ] Project switch intent works if wired on Path C respond path

### Record

| Result | Date | Tester | Notes |
|--------|------|--------|-------|
| [ ] PASS / PARTIAL / FAIL | | | |

---

## UC-16: Ingestion upload (optional / P2)

**Actor:** Operator  
**Goal:** Document enters triage pipeline.

### Steps

1. Open `/ingest`
2. Upload a small PDF or text file
3. Confirm upload ACK and status

### Pass criteria

- [ ] Upload returns success
- [ ] Triage state visible (approve → fleet chain may be incomplete — note as known gap)

### Record

| Result | Date | Tester | Notes |
|--------|------|--------|-------|
| [ ] PASS / PARTIAL / FAIL / SKIP | | | |

---

## UC-17: Fleet voice write + project bar (confirm required)

**Actor:** Fleet operator  
**Goal:** Project bar + voice/UI trigger FirstMate on the correct fleet slug.

**Warning:** Use only on staging; confirm prompts required.

### Steps

1. Project bar → **ADVoi System** (`advoi`)
2. Say: **"wake firstmate"** — expect confirm prompt naming advoi
3. Say **"no"** — action cancelled
4. Tap **Wake FirstMate** — confirm prompt should also reference **advoi** (not stale fleet profile only)
5. Say **"yes"** only if safe on staging
6. Say **"fleet status"** — verify queue/arm state changed

### Pass criteria

- [ ] Write intent requires confirmation
- [ ] Deny does not execute fleet write
- [ ] UI fleet buttons use project bar slug (`advoi`), not only fleet profile file
- [ ] Accept produces fleet spoken result (if live bridge enabled)

### Record

| Result | Date | Tester | Notes |
|--------|------|--------|-------|
| [ ] PASS / PARTIAL / FAIL / SKIP | | | |

---

## Full sign-off summary

| Use case | Result | Blocker |
|----------|--------|---------|
| UC-01 Open PWA | | |
| UC-02 Project UI | | |
| UC-03 Morning pulse | | |
| UC-04 Voice connect | | |
| UC-05 Six frames | | |
| UC-06 Voice project switch | | |
| UC-07 Meta operators | | |
| UC-08 Agents preset | | |
| UC-09 Chain/queue/mirror | | |
| UC-10 Add feature | | |
| UC-11 Home briefs A17 | | |
| UC-12 Aether/dashboard | | |
| UC-13 Errors | | |
| UC-14 Briefs tab | | |
| UC-15 Path C | | |
| UC-16 Ingestion | | |
| UC-17 Fleet write | | |

**Overall:** [ ] **OPERATIONAL** / [ ] **PARTIAL** / [ ] **NOT READY**

**Sign-off date:** _______________ **Approver:** _______________

---

## Known gaps (do not fail UC for these alone)

| Gap | Affects | Workaround |
|-----|---------|------------|
| Session project override resets on API restart | UC-02, UC-06 | Re-select project after redeploy |
| Custom features client-only | UC-10 | No backlog ticket yet |
| Gate slug vs fleet slug mismatch | UC-12 | Document which source wins |
| `LETTA_ENABLED=false` on VPS | UC-05 E | Memory frame still works via Hindsight |
| Ingestion approve → fleet | UC-16 | Mark SKIP until pipeline complete |
| Live squad webhook mock | UC-17 | SKIP unless `ADVOI_SQUAD_MOCK=false` |

---

## On failure

1. Note use case ID and step number in [MANUAL-TEST-TRACKER.md](MANUAL-TEST-TRACKER.md) Known bugs.
2. VPS logs: `docker compose --profile app logs advoi-voice --tail 80`
3. Repair env: `bash scripts/repair-vps-env.sh`
4. Redeploy: `bash scripts/staging-redeploy.sh`
5. Re-run automated pre-checks before retrying human UC.

---

## Quick copy: 15-minute smoke script

For a single tester on phone:

```
1. Open advoi.keyteller.com — hard refresh
2. Project bar → switch to ADVoi System
3. Connect voice → hear greeting
4. Say "systems pulse"
5. Say "switch to gem dev shop"
6. Tap Option A (fleet)
7. Agents tab → run morning preset
8. Home → check briefs section
9. Mark UC-01,02,03,04,06,08,11 PASS/FAIL
```