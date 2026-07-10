# Current state

Honest snapshot of ADVoi before planning next work.

**Last updated:** 2026-07-10  
**Stage:** Build 1.5+ (voice + PWA + **6 agents** + operators + squads + dashboard)

---

## Start here

| Doc | Read when you want to know... |
|-----|-------------------------------|
| **[SYSTEM-STATUS.md](SYSTEM-STATUS.md)** | **Authoritative** — what we have, gaps, commands |
| **[WHAT-WE-DID-2026-07-10.md](WHAT-WE-DID-2026-07-10.md)** | Sprint changelog (multi-agent platform) |
| **[DEVELOPMENT-MILESTONES.md](DEVELOPMENT-MILESTONES.md)** | Prioritized milestones M0-M7 |
| [what-we-have.md](what-we-have.md) | Module-level inventory |
| [gaps-and-blockers.md](gaps-and-blockers.md) | Prioritized open work (incl. GAP-013 promote park) |
| [ALIGNMENT-LOG.md](ALIGNMENT-LOG.md) | Batch / staging drift alignment entries |
| [improvement-roadmap.md](improvement-roadmap.md) | Phased plan (Phases 1-4) |
| [ROADMAP-VALIDATION.md](../operations/ROADMAP-VALIDATION.md) | T0–T3 gates, M1–M10, gap register |
| [MANUAL-TEST-TRACKER.md](../operations/MANUAL-TEST-TRACKER.md) | Human tests: tested / not tested / bugs |
| [BUILD-1.5-FINAL.md](BUILD-1.5-FINAL.md) | Build exit criteria |
| [path-to-full-system.md](path-to-full-system.md) | Path to full system |
| [../reviews/EXTERNAL-ENGINEERING-ARCHITECTURE-REVIEW.md](../reviews/EXTERNAL-ENGINEERING-ARCHITECTURE-REVIEW.md) | External engineering/architecture review pack |

---

## One-line status

**6 agents + 4 squads built and orchestrable. Develop `3d5a00d` ahead of staging VPS `5d50805` (GAP-013 SSH promote parked). Bootstrap T2 green @ advoi-staging — not tip parity. Human E2E open, not blocking dev.**

---

## Maturity assessment

| Label | Meaning |
|-------|---------|
| **Built** | Code exists, unit tests pass |
| **Staging-ready** | Works on VPS when env healthy |
| **Validated** | Human or CI E2E sign-off recorded |
| **Vision** | Designed, not implemented |

| Area | Level |
|------|-------|
| API + 6 frames + 6 agents + squads | Built |
| LiveKit voice pipeline | Built |
| PWA (Path A) | Built (home briefs surface + chips) |
| Client voice (Path B) | Built (auto fallback to server) |
| Server voice (Path C) | Built |
| Staging infra (Traefik, env) | Staging-ready |
| Human voice E2E | **Not validated** |
| Operators + dashboard | Built |
| Aether / Guardian / squads (code) | Built (VPS enablement open) |
| Letta / OTel on VPS | Partial |

---

## Live staging snapshot (2026-07-10 ops review)

```
https://advoi-staging.keyteller.com/api/health  → 200 (6/6 agents, stage=voice-pwa-2)
t2-staging-smoke.sh (ADVOI_BASE_URL=staging)    → PASS (bootstrap SHA only)
staging-signoff-precheck.sh                     → PASS exit 0 (sla_ok=false ~1.2s)
Staging VPS tree                                → 5d50805 (behind develop 3d5a00d)
Promote                                         → PARKED GAP-013 (SSH host key)
Fleet state                                     → /data/staging-state.md
```

---

## Critical path (do these first)

1. Human E2E on phone — [E2E-SIGNOFF.md](../operations/E2E-SIGNOFF.md)
2. Voice confirm test — say "queue review" then "yes"
3. Record PASS in DEV-LOG
4. Close `.aether/STAGE.md` exit criteria

Everything else (Path B, latency, Letta, dashboard) layers on a signed-off Path A baseline.

---

## Stale docs warning

These predate Build 1.5 and understate progress:

- `docs/PLAN-SETUP-REVIEW.md` — banner points here
- `web/README.md` — updated for home briefs surface (2026-07-10); re-check if it drifts again
- `docs/dev-log/DEV-LOG.md` — needs E2E sign-off entry

**Source of truth:** this folder + `docs/architecture/` + `.aether/STAGE.md`.