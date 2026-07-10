# Aether directives (proactive)

Generated **2026-07-10 00:34 UTC** by `aether-proactive-cycle.sh`. Independent of Paperclip.

| Field | Value |
|-------|-------|
| Venture | /data/projects/advoi |
| Top severity | none |
| Top finding | no diff to review |
| Findings | 1 |
| Decisions logged | 2 |
| Events logged | 2 |
| Principles version | 1.0.0-advoi |

## Venture context (read-only)

| Signal | Value |
|--------|-------|
| Stage | Build |
| Active bet | Stage 1 Voice + PWA |
| Last decision | ADR-026 Memory stack |
| FirstMate in-flight | 0 |
| Diff window | main...HEAD (no changes) |
| Awareness agents | governance, context, product, fleet, voice, llm_pm |

### Agent runs

| Agent | Status | Summary |
|-------|--------|---------|
| governance | ok | 0 governance finding(s) |
| context | ok | stage=Build in_flight=0 no diff to review |
| product | ok | 0 open checklist item(s) |
| fleet | ok | 0 fleet signal(s) |
| voice | ok | staging voice path present |
| llm_pm | skipped | disabled (set AETHER_LLM_PM=1) |

## Findings

- **[NONE]** [audit] no diff to review

## Governance actions

| Priority | Action |
|----------|--------|
| none | Audit-only cycle — no ship candidates; log and continue |

## Triggers (no Paperclip required)

- Cron: `install-aether-proactive-cron.sh`
- Strengthen: `strengthen-aether-governance.sh --sync`
- Gate: `bash /opt/firstmate/scripts/fm-aether-gate.sh` with `FM_ACTIVE_PROJECT=advoi`
- Bootstrap: `bash scripts/aether-bootstrap.sh`

## Commands

```bash
bash /opt/aether/scripts/strengthen-aether-governance.sh --sync --notify
bash /opt/aether/scripts/aether-cli.sh proactive --project /data/projects/advoi --aether-source /opt/aether
FM_ACTIVE_PROJECT=advoi bash /opt/firstmate/scripts/fm-aether-gate.sh
```
