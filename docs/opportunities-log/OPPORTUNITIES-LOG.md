# ADVoi Opportunities Log

> Deferred work, follow-up ideas, and improvement opportunities surfaced during fleet batches.  
> Not blockers — items worth revisiting when capacity or priority allows.

---

## How to Use This Log

1. **Add an entry** when work is intentionally deferred, a better approach is spotted, or infra debt is identified during a batch.
2. **Link milestones** (M1–M9) and roadmap tiers (T0–T3) where relevant.
3. **Status values:** `Open` | `Scheduled` | `Promoted` | `Won't Do`
4. Cross-reference [ROADMAP-VALIDATION.md](../operations/ROADMAP-VALIDATION.md) and [gaps-and-blockers.md](../current-state/gaps-and-blockers.md).

### Entry Template

```markdown
## OPP-YYYY-NNN: Short Title

**Logged:** YYYY-MM-DD  
**Batch:** batch-YYYY-MM-DD  
**Status:** Open  
**Milestone:** M# (if applicable)  
**Priority:** P0 | P1 | P2 | P3

### Context
[Why this came up during the batch]

### Opportunity
[What we could do and expected benefit]

### Deferral Reason
[Why not now]

### Next Action
[Concrete step when promoted — owner, tier, proof]
```

---

## Opportunity Index

| ID | Title | Status | Batch | Milestone |
|----|-------|--------|-------|-----------|
| OPP-2026-001 | M2 human E2E sign-off session | Open | 2026-07-10 | M2 |
| OPP-2026-002 | M4 OTel + Letta enablement on VPS | Open | 2026-07-10 | M4 |
| OPP-2026-003 | Live squad webhooks (`ADVOI_SQUAD_MOCK=false`) | Open | 2026-07-10 | M5 |

---

## OPP-2026-001: M2 human E2E sign-off session

**Logged:** 2026-07-10  
**Batch:** batch-2026-07-10  
**Status:** Open  
**Milestone:** M2  
**Priority:** P0

### Context

Six-agent control plane, operator voice, fleet bridge, and staging redeploy shipped in the 2026-07-10 sprint. Automated T0/T2 coverage is strong (224 pytest). Path A human mic + TTS sign-off remains open per [MANUAL-TEST-TRACKER.md](../operations/MANUAL-TEST-TRACKER.md).

### Opportunity

A focused **15-minute** human session would close M2.1–M2.7: Path C spot check, staging Connect + greeting TTS, frame taps, two-turn Guardian confirm, operator intents, fleet voice summary, and [E2E-SIGNOFF.md](../operations/E2E-SIGNOFF.md) copy-in.

### Deferral Reason

Human E2E does **not** block development (per roadmap policy). Engineering priority went to control-plane delivery and staging parity (M1). Device session scheduled when operator has a quiet window.

### Next Action

Run [MANUAL-TEST-TRACKER quick session](../operations/MANUAL-TEST-TRACKER.md#quick-manual-session-15-min); record PASS/FAIL in E2E-SIGNOFF; promote to M2 complete in ROADMAP-VALIDATION.

---

## OPP-2026-002: M4 OTel + Letta enablement on VPS

**Logged:** 2026-07-10  
**Batch:** batch-2026-07-10  
**Status:** Open  
**Milestone:** M4  
**Priority:** P2

### Context

Code paths exist: operational memory retain on run-six, `GET /api/diagnostics/platform`, Letta client + JSONL fallback. VPS still runs with `LETTA_ENABLED` and `OTEL_ENABLED` off — observability and operational memory are staging-ready in code only.

### Opportunity

Enable Letta at `/opt/letta` and OTel collector sidecar on staging. Unlocks M4.4–M4.6: recall verification, distributed traces, trace IDs in guardian events. Improves incident response and memory continuity across squad dispatches.

### Deferral Reason

P2 behind M1 staging parity and M2 human sign-off. No production claim requires traces yet; JSONL fallback covers local dev.

### Next Action

VPS: `LETTA_ENABLED=true`, deploy Letta compose; `OTEL_ENABLED=true` + collector; T2 verify via `/api/diagnostics/platform` and guardian event trace fields.

---

## OPP-2026-003: Live squad webhooks (`ADVOI_SQUAD_MOCK=false`)

**Logged:** 2026-07-10  
**Batch:** batch-2026-07-10  
**Status:** Open  
**Milestone:** M5  
**Priority:** P2

### Context

Squad dispatch bridge is complete in mock mode: 4 squads, `dispatch_squads=true`, voice "dispatch all squads", dashboard controls. Staging uses `ADVOI_SQUAD_MOCK=true` — no real FirstMate/Discord webhook traffic.

### Opportunity

Set live webhook URL on VPS and `ADVOI_SQUAD_MOCK=false`. Closes M5.4–M5.5; enables M5.6 Discord crew ACK visible in fleet read. Validates end-to-end squad orchestration beyond pytest mocks.

### Deferral Reason

Mock path sufficient for 6-agent and dashboard MVP validation. Live webhooks need Discord workflow documentation (M8.4) and operator confirm discipline before flipping staging flag.

### Next Action

Configure webhook URL in staging `.env`; `ADVOI_SQUAD_MOCK=false`; T2 dispatch-all curl + T3 Discord ACK check; update SYSTEM-STATUS when live.

---

*End of opportunities log. Add new entries above this line.*