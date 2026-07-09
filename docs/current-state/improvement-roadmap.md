# Improvement roadmap

Prioritized work after current state. Ordered by impact on **testable staging** first, then product depth.

## Phase 1 — Stabilize staging (1-2 days)

| # | Task | Outcome | Status |
|---|------|---------|--------|
| 1.1 | Commit env repair + deploy scripts; verify on VPS | No more post-deploy 404 | [x] Done |
| 1.2 | Mandatory `OPENAI_API_KEY` check in `voice-smoke-test.sh` / diagnostics | Fail fast when voice will crash | [x] Done |
| 1.3 | Human E2E checklist in `docs/operations/staging-runbook.md` | Signed voice validation | [x] Done |
| 1.4 | Update `.aether/STAGE.md` to 1.5 criteria | Governance matches reality | [x] Done |
| 1.5 | `plain_copy` + frame labels without em dashes | UX consistency | [x] Done |

## Phase 2 — Multi-agent depth (3-5 days)

| # | Task | Outcome | Status |
|---|------|---------|--------|
| 2.1 | Review queue Postgres persistence + API | Real queue, not stub | [x] Done |
| 2.2 | Desktop brief link generation | Review frame delivers URL | [x] Done |
| 2.3 | Agent `last_run` in PWA UI | User sees fleet/briefs freshness | [x] Done |
| 2.4 | Reduce demo interval via `ADVOI_AGENT_INTERVAL_SECS=15` on staging only | Faster cache for testers | [x] Done |
| 2.5 | CI job: pytest + `agents-smoke-test` against docker compose | Regression gate | [x] Done (`agents-smoke` job in `advoi-ci.yml`) |

## Phase 3 — Voice quality (1-2 weeks)

| # | Task | Outcome | Status |
|---|------|---------|--------|
| 3.1 | Intent routing (keyword or lightweight classifier) | Speech maps to frames | [x] Done |
| 3.2 | Warmth layer in prompts (mirror user phrases) | Less robotic server TTS | [x] Done |
| 3.3 | Client voice path: Kokoro + Parakeet + `/voice-local` | Private low-latency option | [x] Done |
| 3.4 | `POST /api/voice/respond` | STT → LLM → TTS loop without LiveKit | [x] Done |
| 3.5 | Latency metrics (first byte, round-trip) | Target under 800ms perceived | [x] Partial (`/api/diagnostics/latency` + SLA; full mic-STT-TTS TBD) |
| 3.6 | Server voice path (`/voice-server`, `/api/voice/speak`) | No WebGPU; browser STT + API TTS | [x] Done |
| 3.7 | Fourth agent `systems-pulse` + Option D | Parallel fleet + briefs | [x] Done |

## Phase 4 — Platform (in progress)

| # | Task | Outcome | Status |
|---|------|---------|--------|
| 4.0 | Request trace middleware + guardian confirmation module | `x-request-id`, `/api/diagnostics/guardian` | [x] Done |
| 4.0b | Manual test tracker doc | Tested / not tested / bugs without blocking dev | [x] Done |

## Phase 4 — Platform (Aether + Letta scale-up)

| # | Task | Outcome | Status |
|---|------|---------|--------|
| 4.1 | Letta v0.2 enablement (`letta_client`, `operational_bridge`) | Operational memory with JSONL fallback | [x] Done (code); enable on VPS with `LETTA_ENABLED=true` |
| 4.1b | `MemoryRouter` unified via `operational_bridge` | Single recall/retain path | [x] Done |
| 4.2 | Guardian error recovery | Auto-restart + notify | [x] Done |
| 4.3 | Aether venture routing | Portfolio manager integration | [x] Done (`aether/`, API, frame hooks, voice context) |
| 4.3b | Aether lifecycle (`gate` + active venture alignment) | `/api/aether/status`, `advoi aether status` | [x] Done |
| 4.4 | Squad execution via FirstMate | Dispatch bridge + run-six | [x] Done (mock); live webhook open |
| 4.5 | React Flow decision dashboard | Visual frame/agent graph | [x] Partial (`/dashboard` MVP); React Flow open |
| 4.7 | 6-agent orchestration + operators | run-six, stop/restart, capabilities | [x] Done (2026-07-10) |
| 4.8 | Platform diagnostics | `/api/diagnostics/platform`, run_six_ms | [x] Done |
| 4.6 | Ingestion + reporting horizontals | Document and stakeholder outputs | [ ] Open |

## Technical debt

| Item | Recommendation |
|------|----------------|
| Stale `PLAN-SETUP-REVIEW.md` | [x] Banner added pointing to `current-state/` |
| 8 tests mentioned in old docs | **105 tests** in 15 modules; keep `tests/` as source of truth |
| Hermes-only Hindsight | Document fallback when bridge down; optional cloud Hindsight |
| Shelve integration | Fix format or remove from deploy path permanently |
| FastAPI TestClient deprecation | Migrate to httpx2 when upgrading |

## Success metrics (testing ready)

| Metric | Target | Today (2026-07-08) |
|--------|--------|---------------------|
| `pytest` | 100% pass | **190 collected** |
| `agents-smoke-test` | All 4 agents + 4 frames OK | Passes locally + staging API |
| `advoi-orchestrate` | 4-agent parallel + pulse | CLI + API wired |
| `voice-smoke-test` | diagnostics `ok: true` on staging | **Pass** |
| Voice E2E | Greeting + frame TTS heard within 10s of connect | **Open** — human sign-off |
| Agent cache | `last_run` present within 1 interval after deploy | **Pass** — 15s on staging |

## Path to full system

See **[path-to-full-system.md](path-to-full-system.md)** for:
- Definition of "full working system"
- Critical path actions (human E2E first)
- Regression risks
- Quick commands (local + VPS)

**Next milestone:** Phase 4.1 (Letta) and 4.2 (Guardian recovery). Human E2E is tracked in [MANUAL-TEST-TRACKER.md](../operations/MANUAL-TEST-TRACKER.md) — not a development gate.