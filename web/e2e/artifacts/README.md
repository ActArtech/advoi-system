# UI state / SLA chip artifacts

Manual or Playwright capture targets for Path A PWA chips:

- `ui-state-chip.png` — status chip showing one of:
  `Idle` | `Connecting` | `Connected` | `Frame running` | `Confirm pending` | `Error`
  Stub: `../voice-session-state.spec.ts` (ship #1)

- `sla-latency-chip.png` — SLA chip next to the state chip, fed by
  `GET /api/diagnostics/latency` (`frame_run_ms`, `run_six_ms`).
  Empty/error: `SLA —` / `SLA err`. Populated: `SLA ok · frame … · six …`.
  Stub: `../voice-session-latency.spec.ts` (ship #2)
