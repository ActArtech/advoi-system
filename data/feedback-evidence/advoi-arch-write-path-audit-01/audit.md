# Architecture: Guardian write-path audit (fm-bridge + fleet)

**Task:** `advoi-arch-write-path-audit-01`  
**Branch:** `fm/advoi-arch-write-path-audit-01`  
**Baseline:** develop @ `6f29565`  
**Scope:** Every `fm-bridge` / `invoke_fleet_trigger` / fleet write path — must evaluate Guardian first  
**Reference:** `docs/architecture/06-vertical-boundaries.md` · `docs/reviews/ARCHITECTURE-DATA-MEMORY-REVIEW.md`  
**Companion pattern:** `data/feedback-evidence/advoi-memory-retain-audit-01/audit.md`

---

## Rules (vertical boundaries)

| Rule | Source |
|------|--------|
| **All consequential writes** (fleet trigger, ingestion dispatch, review side effects) evaluate Guardian first | 06-vertical-boundaries Guardian write rule |
| Fleet live invoke must not skip Guardian | Fleet vertical: *Must not skip Guardian on live invoke* |
| `fm-bridge` invoke only via Guardian-gated fleet / api paths | Fleet audit line in 06 |
| Voice must not shell to FirstMate / import bridge for dispatch | Voice vertical: *Must not invoke fm-bridge* |
| Ingestion chain: `route → (approve) → guardian → fleet` | Ingestion vertical |
| Aether must not invoke `fm-bridge` | Aether vertical |

Target chain:

```text
API / voice / ingestion → evaluate_fleet_confirmation (or fleet_trigger_from_voice)
                       → invoke_fleet_trigger(guardian_allowed=True | guardian_status=allowed)
                       → resolve_fleet_exec → scripts/fm-bridge.sh → fm-hermes-trigger.sh
```

---

## Inventory: production write sites

| File:line (post-fix) | Path | Guardian? | Severity (pre → post) |
|----------------------|------|-----------|------------------------|
| `advoi/fleet/trigger.py` `fleet_trigger_from_voice` | Structured actions (wake/start/backlog/stop) | **yes** — `evaluate_fleet_confirmation` then invoke with `guardian_status="allowed"` | OK |
| `advoi/fleet/trigger.py` `invoke_fleet_trigger` | Low-level fm-bridge shell | **enforced** — requires `guardian_allowed` / `guardian_status=allowed` when confirmation on | **P0 → fixed** |
| `advoi/api/app.py` `POST /api/fleet/trigger` | HTTP fleet actions | **yes** — only `fleet_trigger_from_voice` | Latent dead unguarded branch **P0 → removed** |
| `advoi/ingestion/pipeline.py` `dispatch_item_dev` | Approve → dispatch | **yes** — gate then `guardian_allowed=True` on free-form work | Convention-only → **enforced** |
| `advoi/voice/respond.py` `_reply_operator_intent` | Voice fleet intents | **yes** — `fleet_trigger_from_voice` | OK (P1 boundary: voice still imports fleet) |
| `advoi/voice/intent_processor.py` | LiveKit voice path | **yes** — gate + `fleet_trigger_from_voice` via respond | OK |
| `scripts/fm-bridge.sh` | Shell adapter | N/A — pure forwarder; no Python gate | OK (must only be reached via gated Python) |

## Inventory: bridge resolution / shell

| File | Role | Allowed? |
|------|------|----------|
| `advoi/fleet/bridge.py` | Resolve `fm-bridge.sh` / trigger script | **yes** — fleet package only |
| `advoi/fleet/trigger.py` | Sole `create_subprocess_exec` to bridge | **yes** |
| `scripts/fm-bridge.sh` | `exec` to `fm-hermes-trigger.sh` | **yes** — adapter |
| Other `advoi/**` packages | Direct bridge / hermes trigger | **none found** |

## Inventory: non-fm-bridge fleet *tree* writes (out of P0 shell scope)

| File | Kind | Notes |
|------|------|-------|
| `advoi/aether/publish_atomic.py` | Writes gate/proactive/directives under `FIRSTMATE_FLEET_PATH` | Architecture tension (aether “must not write fleet tree”); **not** fm-bridge spawn — flagged P2, not fixed this ship |
| `advoi/aether/gate_export.py` | Repo export + optional PEL | Not fm-bridge |
| `advoi/aether/gate.py` | **Read** fleet gate artifact | OK |

---

## Violations summary

| ID | Severity | Description | Action |
|----|----------|-------------|--------|
| **V1** | **P0 fixed** | `invoke_fleet_trigger` had **no Guardian hard gate**. Any importer could shell to fm-bridge when `ADVOI_CONFIRMATION_REQUIRED=true` (default) without `evaluate_fleet_confirmation`. | Require `guardian_allowed=True` or `guardian_status="allowed"` when confirmation policy is on; reject with `status=guardian_required`. |
| **V2** | **P0 fixed** | `POST /api/fleet/trigger` retained a dead branch calling bare `invoke_fleet_trigger(f"work {task}")` with no Guardian. Unreachable for the four allowed actions but a latent leak if control flow changed. | Remove free-form invoke; all actions go through `fleet_trigger_from_voice` only. |
| **V3** | **P0→hardened** | Ingestion default dispatch used bare `invoke_fleet_trigger` after a separate gate (correct by convention, not by contract). | Pass `guardian_allowed=True` + `guardian_status="allowed"` + `caller="ingestion"` after gate. |
| **V4** | P1 (deferred) | `voice` imports `advoi.fleet.trigger` / session for operator dispatch | Known pressure point in 06; still Guardian-gated via `fleet_trigger_from_voice`. Prefer thin routing/API later. |
| **V5** | P2 (deferred) | `aether.publish_atomic` writes fleet tree files | Outside fm-bridge spawn path; revisit vertical rules vs intentional publish. |

### Counts

| Metric | Count |
|--------|------:|
| **P0 fm-bridge direct-write leaks fixed** | **2** (V1 structural + V2 API) |
| **P0 hardened (contract)** | **1** (V3 ingestion) |
| **P1 deferred** | **1** (V4 voice import) |
| **P2 deferred** | **1** (V5 aether tree publish) |
| **Production shell sites outside fleet package** | **0** |

---

## Fixes shipped

1. **`_guardian_permits_fleet_invoke`** in `advoi/fleet/trigger.py` — hard gate on live invoke.
2. **Ingestion** passes explicit post-gate tokens on free-form arm/work.
3. **API** fleet trigger is Guardian-only via `fleet_trigger_from_voice` (no bare invoke).
4. **T0 guard:** `tests/test_write_path_audit.py` + this report.

---

## Guardrails

- `tests/test_write_path_audit.py` — static + behavioral assertions
- Runtime: `invoke_fleet_trigger(..., guardian_allowed=False)` → `guardian_required` when confirmation on

---

## Changelog

| Date | Change |
|------|--------|
| 2026-07-10 | Initial write-path audit @ `6f29565`; P0 hard gate + report |
