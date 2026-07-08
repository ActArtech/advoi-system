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
| 3.5 | Latency metrics (first byte, round-trip) | Target under 800ms perceived | [ ] Open |

## Phase 4 — Platform (later)

| # | Task | Outcome |
|---|------|---------|
| 4.1 | Letta v0.2 enablement | Operational memory |
| 4.2 | Guardian error recovery | Auto-restart + notify |
| 4.3 | Aether venture routing | Portfolio manager integration |
| 4.4 | Squad execution via FirstMate | Voice triggers fleet jobs |
| 4.5 | React Flow decision dashboard | Visual frame/agent graph |
| 4.6 | Ingestion + reporting horizontals | Document and stakeholder outputs |

## Technical debt

| Item | Recommendation |
|------|----------------|
| Stale `PLAN-SETUP-REVIEW.md` | [x] Banner added pointing to `current-state/` |
| 8 tests mentioned in old docs | Update to 37+; keep `tests/` as source of truth |
| Hermes-only Hindsight | Document fallback when bridge down; optional cloud Hindsight |
| Shelve integration | Fix format or remove from deploy path permanently |
| FastAPI TestClient deprecation | Migrate to httpx2 when upgrading |

## Success metrics (testing ready)

| Metric | Target |
|--------|--------|
| `pytest` | 100% pass |
| `agents-smoke-test` | All 3 agents + 3 frames OK |
| `voice-smoke-test` | diagnostics `ok: true` on staging |
| Voice E2E | Greeting + frame TTS heard within 10s of connect |
| Agent cache | `last_run` present within 1 interval after deploy |