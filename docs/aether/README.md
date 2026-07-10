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

**T0:** `uv run pytest tests/test_aether_proactive_schema.py tests/test_aether_gate_artifacts.py -q`
