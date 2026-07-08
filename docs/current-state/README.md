# Current state

Honest snapshot of ADVoi before planning next work.

**Last updated:** 2026-07-08  
**Commit:** `48e7645`  
**Stage:** Build 1.5 (voice + PWA + multi-agent)

---

## Start here

| Doc | Read when you want to know... |
|-----|-------------------------------|
| **[BUILD-1.5-FINAL.md](BUILD-1.5-FINAL.md)** | **Gap table answered** — done vs open, your 15-min checklist |
| **[path-to-full-system.md](path-to-full-system.md)** | How close we are to done and what to do next |
| [what-we-have.md](what-we-have.md) | Everything that is built and tested |
| [gaps-and-blockers.md](gaps-and-blockers.md) | What still blocks production validation |
| [improvement-roadmap.md](improvement-roadmap.md) | Phased plan (Phases 1-4) |

---

## One-line status

**Built and staging-ready. Not human-validated.** Open `https://advoi.keyteller.com`, connect voice, confirm you hear TTS — then record in [E2E-SIGNOFF.md](../operations/E2E-SIGNOFF.md).

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
| API + 3 frames + 3 agents | Built |
| LiveKit voice pipeline | Built |
| PWA (Path A) | Built |
| Client voice (Path B) | Built (not device-validated) |
| Staging infra (Traefik, env) | Staging-ready |
| Human voice E2E | **Not validated** |
| Letta / Guardian / Aether | Vision |

---

## Live staging snapshot (2026-07-08)

```
https://advoi.keyteller.com/api/health     → 200, agents 3/3
https://advoi.keyteller.com/api/diagnostics/voice → ok: true
pytest local                               → 105 passed
VPS containers                             → all Up
ADVOI_AGENT_INTERVAL_SECS                  → 15 (staging)
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
- `web/README.md` — still says frame buttons are "Stage 2" (they are built)
- `docs/dev-log/DEV-LOG.md` — needs E2E sign-off entry

**Source of truth:** this folder + `docs/architecture/` + `.aether/STAGE.md`.