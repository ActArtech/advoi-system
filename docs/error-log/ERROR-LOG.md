# ADVoi Error Log — Guardian Agent

> Failure detection, resolution tracking, and learning memory for the Guardian agent.  
> Guardian stays dormant until an issue is detected, then activates, fixes, and logs.

---

## How to Use This Log

### Guardian Workflow

```
Issue Detected → Guardian Activated → Analyze → Fix/Recover → Log → Notify
     │                                                                      │
     └──── "Issue Detected" notification ────────────────── "Issue Resolved" ──┘
```

### Entry Template

```markdown
## ERR-YYYY-NNN: Short Title

**Detected:** YYYY-MM-DD HH:MM UTC  
**Resolved:** YYYY-MM-DD HH:MM UTC | *Pending*  
**Severity:** Critical | High | Medium | Low  
**Status:** Detected | Investigating | Resolved | Escalated | Recurring  
**Guardian Action:** Auto-fixed | Manual-fix | Escalated-to-Aether | User-notified

### Affected Components
- [ ] Aether
- [ ] Guardian
- [ ] Squad: [callsign]
- [ ] Voice Layer (LiveKit/Pipecat)
- [ ] FirstMate / Hermes
- [ ] Ingestion Engine
- [ ] Reporting Engine
- [ ] PostgreSQL / Data Layer
- [ ] Web PWA
- [ ] VPS Infrastructure

### Detection
**Trigger:** [What caused Guardian to wake? e.g., health check failure, squad drift, error rate spike]  
**Symptoms:** [Observable behavior]  
**Error Message / Stack:**
```
[paste error or log excerpt]
```

### Root Cause
[Guardian's analysis of why this happened]

### Resolution
**Fix Applied:** [What Guardian or human did to resolve]  
**Verification:** [How resolution was confirmed]  
**Prevention:** [Guardian memory update — rule/patch to prevent recurrence]

### Notifications Sent
| Time | Type | Channel | Recipient |
|------|------|---------|-----------|
| | Issue Detected | App / Voice | User |
| | Issue Resolved | App | User |
| | Info | App | Aether |

### Guardian Learning Entry
**Pattern ID:** GP-XXX  
**Category:** [e.g., squad-drift, memory-corruption, deploy-failure, model-timeout, auth-failure]  
**Reusable Fix:** [Yes/No — can this fix be auto-applied next time?]  
**Confidence:** High | Medium | Low

### Related
- ADR: [if architectural change needed]
- ERR-YYYY-NNN: [if related to previous error]
- Squad: [callsign if applicable]
```

---

## Severity Definitions

| Severity | Definition | Guardian Response | Notification |
|----------|------------|-------------------|--------------|
| **Critical** | System down, data loss risk, security breach | Immediate fix attempt; voice + app notification | Voice + App |
| **High** | Major feature broken, squad stuck, deploy failure | Fix within session; app notification | App (voice if user-facing) |
| **Medium** | Degraded performance, non-blocking errors, drift detected | Log + fix in next cycle; app notification | App |
| **Low** | Warnings, minor quality issues, stale data | Log + include in optimization review | App (batched) |

---

## Error Categories (Guardian Memory Taxonomy)

| Category ID | Name | Description | Auto-Fix Eligible |
|-------------|------|-------------|---------------------|
| `GP-001` | **squad-drift** | Squad deviates from mission or architecture standards | Partial |
| `GP-002` | **squad-stuck** | Squad in loop or blocked beyond timeout | Yes |
| `GP-003` | **memory-corruption** | State inconsistency between Aether/squad layers | No — escalate |
| `GP-004` | **memory-sync-failure** | Debrief or state sync failed | Yes |
| `GP-005` | **deploy-failure** | Agentic deploy or container crash | Yes |
| `GP-006` | **service-down** | Core service not responding (LiveKit, Pipecat, Postgres) | Yes |
| `GP-007` | **model-timeout** | LLM request timeout or rate limit | Yes |
| `GP-008` | **model-quality** | Hallucination, repetition, confidence drop | Partial |
| `GP-009` | **token-budget** | Squad/project exceeded daily token budget | Yes |
| `GP-010` | **auth-failure** | PWA/VPS/API authentication error | Partial |
| `GP-011` | **backup-failure** | Backblaze B2 or backup script failed | Yes |
| `GP-012` | **security-anomaly** | Unauthorized access attempt, CrowdSec alert | No — escalate |
| `GP-013` | **staging-push-fail** | Squad staging deployment rejected | Partial |
| `GP-014` | **voice-pipeline** | STT/TTS/LiveKit connection failure | Yes |
| `GP-015` | **ingestion-parse** | Ingestion Engine failed to parse input | Partial |
| `GP-016` | **silence-trigger** | 3-day user silence rule activated | Yes |
| `GP-017` | **guardian-self** | Guardian agent failure (meta) | Escalate to user |

---

## Guardian Memory Schema (Per Fix)

Guardian maintains evolving memory of past errors. Each resolved error contributes:

```json
{
  "pattern_id": "GP-006",
  "occurrence_count": 1,
  "first_seen": "2026-07-07T00:00:00Z",
  "last_seen": "2026-07-07T00:00:00Z",
  "root_causes": ["container OOM after memory spike"],
  "fixes_applied": ["restart service", "increase memory limit in compose"],
  "auto_fix_confidence": "high",
  "affected_components": ["voice-layer"],
  "prevention_rule": "Monitor memory usage; auto-restart at 90% threshold"
}
```

---

## Escalation Rules

| Condition | Action |
|-----------|--------|
| Auto-fix succeeds | Log → Issue Resolved notification |
| Auto-fix fails after 2 attempts | Escalate to Aether with context |
| Strategic/architectural issue | Escalate to Aether immediately |
| Security anomaly | Escalate to user immediately (voice if critical) |
| Data loss risk | Pause affected squad → notify user → await approval |
| Guardian self-failure | Notify user directly; do not recurse |

---

## Error Log Entries

> No errors recorded yet. System scaffold created 2026-07-07.

---

## [2026-07-07] — Log Initialized

**Type:** Scaffold  
**Status:** Complete

Error log template created as part of v0.1.0 documentation scaffold. Guardian agent not yet deployed — this log is ready to receive entries when monitoring and failure detection are wired.

### Monitoring Integration (Planned)

| Source | Guardian Feed |
|--------|---------------|
| Docker/PM2 health checks | `GP-005`, `GP-006` |
| SigNoz / OpenTelemetry traces | `GP-007`, `GP-008`, `GP-014` |
| PostgreSQL connection monitor | `GP-006` |
| Backblaze backup cron | `GP-011` |
| Aether 3-day silence trigger | `GP-016` |
| Squad heartbeat / OODA timeout | `GP-002` |
| CrowdSec alerts | `GP-012` |
| OpenRouter rate limits | `GP-007`, `GP-009` |

### Next Steps

- [ ] Wire Guardian activation to health check failures
- [ ] Define auto-fix playbooks for GP-002, GP-005, GP-006, GP-014
- [ ] Connect error log to PostgreSQL `guardian_errors` table
- [ ] Implement two-phase notification (Detected → Resolved)
- [ ] Feed resolved patterns into Guardian evolving memory store

---

## Example Entry (Reference Only — Delete When Real Errors Occur)

```markdown
## ERR-2026-001: Pipecat Voice Agent Container OOM

**Detected:** 2026-07-07 14:30 UTC  
**Resolved:** 2026-07-07 14:32 UTC  
**Severity:** High  
**Status:** Resolved  
**Guardian Action:** Auto-fixed

### Affected Components
- [x] Voice Layer (LiveKit/Pipecat)

### Detection
**Trigger:** Docker health check failure — container exit code 137  
**Symptoms:** Voice sessions disconnect; no STT response  
**Error Message:**
```
pipecat-agent | Killed (OOM)
```

### Root Cause
Pipecat container memory limit (512MB) exceeded during concurrent STT + LLM processing.

### Resolution
**Fix Applied:** Restarted container; increased memory limit to 1GB in docker-compose  
**Verification:** Health check passing; test voice session successful  
**Prevention:** Added memory monitoring alert at 85% threshold (GP-006 pattern)

### Notifications Sent
| Time | Type | Channel | Recipient |
|------|------|---------|-----------|
| 14:30 | Issue Detected | App | User |
| 14:32 | Issue Resolved | App | User |
| 14:32 | Info | App | Aether |

### Guardian Learning Entry
**Pattern ID:** GP-006  
**Category:** service-down  
**Reusable Fix:** Yes — auto-restart + memory alert  
**Confidence:** High
```

---

*Add new error entries above the example section. Guardian learns from every entry.*