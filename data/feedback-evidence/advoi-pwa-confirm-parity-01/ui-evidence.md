# UI evidence — confirm parity (A15)

## Panel contract (`confirm_pending`)

| Element | Selector | Content |
|---------|----------|---------|
| Panel | `data-testid="confirm-pending"` | Visible when UI state is `confirm_pending` |
| Copy | `data-testid="confirm-copy"` | Guardian prompt (same string as voice TTS / status) |
| Button | `data-testid="confirm-accept"` | Label **Confirm** |

## Paths

1. **Tap frame** (`queue_deep_review` without confirm) → status = confirm copy; panel shows copy + Confirm; chip `confirm_pending`; beacon `confirm_shown`.
2. **Voice intent** same frame phrase → TTS speaks **identical** copy; same panel.
3. **Confirm button** / re-tap / say yes → `confirm_accept` + frame proceeds.

## Model

`web/components/confirmParity.ts` — `confirmCopyFromResponse` prefers `prompt` → `spoken_summary` → `spoken`.

## Automated

- `uv run pytest tests/test_confirm_parity.py` — 12 tests (model + Guardian + API frame/fleet)
- Stub: `web/e2e/voice-session-confirm-parity.spec.ts`
- Screenshot target: `web/e2e/artifacts/confirm-parity.png` (manual/headed Playwright)

## Status line

Status `role="status"` and `confirm-copy` must equal the same Guardian string (no “Connect voice…” suffix mutating the core copy).
