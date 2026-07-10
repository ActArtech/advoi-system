/**
 * Explicit PWA voice-shell UI state machine.
 *
 * States are visible in the status chip. Transitions are driven by:
 * - LiveKit connect / disconnect / media errors
 * - Frame run API lifecycle
 * - Guardian / frame `confirmation_required` responses
 */

export type UiSessionState =
  | "idle"
  | "connecting"
  | "connected"
  | "frame_running"
  | "confirm_pending"
  | "error";

/** Human-visible labels for the status chip (must stay 1:1 with UiSessionState). */
export const UI_STATE_LABELS: Record<UiSessionState, string> = {
  idle: "Idle",
  connecting: "Connecting",
  connected: "Connected",
  frame_running: "Frame running",
  confirm_pending: "Confirm pending",
  error: "Error",
};

/** Ordered list for docs, Playwright stubs, and chip enumeration. */
export const UI_SESSION_STATES: readonly UiSessionState[] = [
  "idle",
  "connecting",
  "connected",
  "frame_running",
  "confirm_pending",
  "error",
] as const;

export type UiSessionEvent =
  | { type: "CONNECT_START" }
  | { type: "CONNECT_OK" }
  | { type: "CONNECT_FAIL" }
  | { type: "DISCONNECT" }
  | { type: "FRAME_START" }
  | { type: "FRAME_OK" }
  | { type: "CONFIRMATION_REQUIRED" }
  | { type: "ERROR" }
  /** LiveKit still up after a non-fatal frame/API failure — restore connected shell. */
  | { type: "FRAME_FAIL_KEEP_VOICE" }
  /** Clear error banner when user retries or dismisses. */
  | { type: "RESET_IDLE" };

export type UiSessionContext = {
  state: UiSessionState;
  /** True while LiveKit room is connected (used to restore after frame/confirm). */
  voiceConnected: boolean;
};

export const INITIAL_UI_SESSION: UiSessionContext = {
  state: "idle",
  voiceConnected: false,
};

function restoreAfterWork(ctx: UiSessionContext): UiSessionContext {
  return {
    ...ctx,
    state: ctx.voiceConnected ? "connected" : "idle",
  };
}

/**
 * Pure reducer for the PWA voice UI state machine.
 * Side-effect free — wire side effects in VoiceSession only.
 */
export function reduceUiSession(
  ctx: UiSessionContext,
  event: UiSessionEvent,
): UiSessionContext {
  switch (event.type) {
    case "CONNECT_START":
      // Keep frame/confirm UI if voice is reconnecting mid-work (rare).
      if (ctx.state === "frame_running" || ctx.state === "confirm_pending") {
        return ctx;
      }
      return { ...ctx, state: "connecting" };

    case "CONNECT_OK":
      // Preserve activity states; only mark transport up.
      if (ctx.state === "frame_running" || ctx.state === "confirm_pending") {
        return { ...ctx, voiceConnected: true };
      }
      return { state: "connected", voiceConnected: true };

    case "CONNECT_FAIL":
      return { state: "error", voiceConnected: false };

    case "DISCONNECT":
      return { state: "idle", voiceConnected: false };

    case "FRAME_START":
      return { ...ctx, state: "frame_running" };

    case "CONFIRMATION_REQUIRED":
      return { ...ctx, state: "confirm_pending" };

    case "FRAME_OK":
      return restoreAfterWork(ctx);

    case "FRAME_FAIL_KEEP_VOICE":
      if (ctx.voiceConnected) {
        return { ...ctx, state: "connected" };
      }
      return { ...ctx, state: "error" };

    case "ERROR":
      return { ...ctx, state: "error" };

    case "RESET_IDLE":
      return {
        state: ctx.voiceConnected ? "connected" : "idle",
        voiceConnected: ctx.voiceConnected,
      };

    default:
      return ctx;
  }
}

export function uiStateLabel(state: UiSessionState): string {
  return UI_STATE_LABELS[state];
}

/** CSS module class key suffix matching VoiceSession.module.css (dot.idle, chip.frame_running, …). */
export function uiStateClass(state: UiSessionState): string {
  return state;
}
