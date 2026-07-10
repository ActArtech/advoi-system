# ADVoi Aether feed (`docs/aether/`)

Proactive cycle outputs for FirstMate’s `fm-aether-gate.sh` when `FM_ACTIVE_PROJECT=advoi`: `aether-proactive-latest.json` and `AETHER-DIRECTIVES.md` are the gate-readable feed path (project principles and stage live under repo-root `.aether/`). This directory unblocks the advoi PEL path (PORTFOLIO-SYSTEM-MOAT **R2** / next `advoi-analytics-pel-schema-01`) and supports roadmap portfolio ops (**M9**) alongside memory/observability (**M4**); regenerate via Aether proactive, validate with `bash scripts/aether-bootstrap.sh` then `FM_ACTIVE_PROJECT=advoi bash /opt/firstmate/scripts/fm-aether-gate.sh` (exit 0 PASS or 1 PASS_AUDIT_ONLY).

## Schema contract

| File | Role |
|------|------|
| `aether-proactive-latest.json` | Latest proactive feed artifact (gate input) |
| `aether-proactive-latest.schema.json` | JSON Schema for that artifact |
| `AETHER-DIRECTIVES.md` | Human-readable directives companion |

**Required fields:** `project`, `mode` (`"proactive"`), `findings` (non-empty array of finding objects with `agent`, `severity`, `category`, `message`).

**Python validator:** `advoi.aether.proactive_schema.validate_proactive_payload` / `validate_proactive_file`.

**T0:** `uv run pytest tests/test_aether_proactive_schema.py tests/test_aether_gate_artifacts.py tests/test_aether_feed_cron.py tests/test_aether_publish_atomic.py tests/test_aether_gate_export.py -q`

## Fleet feed cron (`FM_AETHER_GATE_REQUIRED=1`)

Entrypoint: `scripts/aether-feed-cron.sh` (defaults `FM_AETHER_GATE_REQUIRED=1` and `FM_ACTIVE_PROJECT=advoi`).

| Gate exit | Meaning | Feed when required=1 |
|-----------|---------|----------------------|
| 0 | PASS | publish |
| 1 | PASS_AUDIT_ONLY | publish |
| ≥2 | FAIL | **skip** — log `aether-feed: skipped — gate FAIL (exit=N) [FM_AETHER_GATE_REQUIRED=1]` |

Pure policy: `advoi.aether.feed_cron.should_skip_feed` / `feed_decision`. Test hooks: `FM_AETHER_GATE_EXIT`, `FM_AETHER_GATE_CMD`, `FM_AETHER_FEED_CMD`.

## Atomic fleet publish (gate + proactive + directives)

Entrypoint: `scripts/aether-publish-atomic.sh` — copies the three Aether surface artifacts into `FIRSTMATE_FLEET_PATH` **all-or-nothing** (temp staging + backup + `os.replace`). On failure, prior fleet files are left intact or restored.

| Fleet artifact | Source (default) |
|----------------|------------------|
| `aether-gate-latest.md` | `FM_AETHER_GATE_REPORT` or `/data/aether-gate-latest.md` |
| `aether-proactive-latest.json` | `docs/aether/aether-proactive-latest.json` |
| `AETHER-DIRECTIVES.md` | `docs/aether/AETHER-DIRECTIVES.md` |

```bash
FM_ACTIVE_PROJECT=advoi bash /opt/firstmate/scripts/fm-aether-gate.sh
bash scripts/aether-publish-atomic.sh
```

Pure API: `advoi.aether.publish_atomic.publish_atomic` / `publish_from_paths`.  
T0: `uv run pytest tests/test_aether_publish_atomic.py -q`

## Gate snapshot export (git + PEL audit)

Entrypoint: `scripts/aether-gate-export.sh` — copies fleet `aether-gate-latest.md` into the advoi tree and/or emits a PEL row so the gate is no longer VPS-only.

| Sink | Default | Notes |
|------|---------|-------|
| Repo path | `data/aether/aether-gate-latest.md` | Git-auditable; optional `--git-commit` (no push) |
| PEL | `governance_decision` / `payload.kind=gate_snapshot` | `source=aether`; needs `DATABASE_URL` or `ADVOI_PEL_MEMORY` |

```bash
bash scripts/aether-publish-atomic.sh
bash scripts/aether-gate-export.sh
# optional local commit of the snapshot file only:
FM_AETHER_GATE_EXPORT_GIT_COMMIT=1 bash scripts/aether-gate-export.sh
```

Pure API: `advoi.aether.gate_export.export_gate_snapshot`.  
Ops runbook: [../operations/README.md](../operations/README.md#aether-gate-snapshot-export-git--pel).  
T0: `uv run pytest tests/test_aether_gate_export.py -q`
