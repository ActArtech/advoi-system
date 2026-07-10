# Operations

Runbooks for local development and staging validation.

**Staging host:** https://advoi-staging.keyteller.com (`/var/www/advoi/staging`)  
**Live host:** https://advoi.keyteller.com  
**Promote:** parked (GAP-013 SSH host key) — develop tip `3d5a00d` ahead of VPS `5d50805`. Green T2 = bootstrap health only.  
**Fleet snapshot:** `/data/staging-state.md` · gaps: [../current-state/gaps-and-blockers.md](../current-state/gaps-and-blockers.md)

| Doc | Audience |
|-----|----------|
| [ROADMAP-VALIDATION.md](ROADMAP-VALIDATION.md) | Milestones M1–M10, validation tiers T0–T3, gap register (incl. GAP-013) |
| [ANALYTICS-FUNNEL.md](ANALYTICS-FUNNEL.md) | PWA connect→frame→confirm→success funnel SQL on PEL `portfolio_events` |
| [MANUAL-TEST-TRACKER.md](MANUAL-TEST-TRACKER.md) | What to test / tested / bugs (does not block dev) |
| [local-testing.md](local-testing.md) | Developers on Windows/Mac/Linux |
| [staging-runbook.md](staging-runbook.md) | VPS deploy and smoke (T2: `scripts/t2-staging-smoke.sh`) |
| [MIGRATIONS.md](MIGRATIONS.md) | Versioned SQL under `deploy/migrations/`, apply order, staging verify (SSH parked) |
| [E2E-SIGNOFF.md](E2E-SIGNOFF.md) | Formal Path A sign-off template (incl. home briefs A17) |
| [BATCH-DOCUMENTATION.md](BATCH-DOCUMENTATION.md) | Fleet batch wrap-up gate, mandatory logs |

See also: [../VPS-SETUP.md](../VPS-SETUP.md) (8-step Aether checklist).

## Aether gate snapshot export (git + PEL)

The fleet runtime file `aether-gate-latest.md` used to be VPS-only (moat gap: no GitHub audit trail). Export it after each gate cycle or on a nightly cron so the artifact is auditable in **git** and/or **`portfolio_events`**.

| Sink | Path / row | When |
|------|------------|------|
| Repo file (git) | `data/aether/aether-gate-latest.md` | Default write; commit via ops or `FM_AETHER_GATE_EXPORT_GIT_COMMIT=1` (no push) |
| PEL | `source=aether`, `type=governance_decision`, `payload.kind=gate_snapshot` | Default when `DATABASE_URL` or `ADVOI_PEL_MEMORY=true` |

**Entrypoint:** `scripts/aether-gate-export.sh` → `advoi.aether.gate_export`.

```bash
# Post-gate (after publish to fleet)
FM_ACTIVE_PROJECT=advoi bash /opt/firstmate/scripts/fm-aether-gate.sh
bash scripts/aether-publish-atomic.sh
bash scripts/aether-gate-export.sh

# Nightly cron example (fleet host)
# 30 2 * * * FIRSTMATE_FLEET_PATH=/opt/firstmate-fleet \
#   bash /data/projects/advoi/scripts/aether-gate-export.sh \
#   >> /var/log/advoi-aether-gate-export.log 2>&1
```

| Flag / env | Effect |
|------------|--------|
| `--no-repo` / `FM_AETHER_GATE_EXPORT_NO_REPO=1` | PEL only |
| `--no-pel` / `FM_AETHER_GATE_EXPORT_NO_PEL=1` | Repo file only |
| `--git-commit` / `FM_AETHER_GATE_EXPORT_GIT_COMMIT=1` | `git add` + `git commit` dest when changed (never push) |
| `FM_AETHER_GATE_REPORT` / `--source` | Override gate source path |
| `FM_AETHER_GATE_EXPORT_DEST` / `--dest` | Override in-repo dest |

**Pure API:** `export_gate_snapshot` / `export_gate_snapshot_sync`.  
**T0:** `uv run pytest tests/test_aether_gate_export.py -q`  
**Feed details:** [../aether/README.md](../aether/README.md).
