# Current state

Snapshot of ADVoi as of **2026-07-08**. Use these docs for honest status before planning next work.

| Doc | Purpose |
|-----|---------|
| [what-we-have.md](what-we-have.md) | Shipped features, tests, scripts |
| [gaps-and-blockers.md](gaps-and-blockers.md) | What blocks production validation |
| [improvement-roadmap.md](improvement-roadmap.md) | Prioritized next work |

## Stage assessment

| Label | Meaning |
|-------|---------|
| **Built** | Code exists and unit tests pass |
| **Staging-ready** | Works on VPS when env and containers healthy |
| **Validated** | E2E smoke passed by a human or CI |
| **Vision** | Designed, not implemented |

**Overall:** Built through Stage 1.5 (voice + PWA + 3 agents + frames). **Not fully validated** on staging due to recurring env/voice blockers.

## Stale docs warning

These files predate multi-agent work and understate progress:

- `docs/PLAN-SETUP-REVIEW.md` (2026-07-07) — says Stage 2 frames out of scope; frames are now built
- `.aether/STAGE.md` — still lists 1.1 exit criteria only
- `docs/dev-log/DEV-LOG.md` — last entries before agent supervisor and local test scripts

Prefer this `current-state/` folder and `architecture/` for accuracy.