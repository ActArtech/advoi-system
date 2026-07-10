/**
 * Thin PWA analytics beacon → POST /api/events → portfolio_events (PEL).
 *
 * No third-party analytics SDK. Fire-and-forget; failures are swallowed.
 * Maps UI state-machine events (voiceSessionState) to PEL event types.
 */

import type { UiSessionEvent } from "./voiceSessionState";

export const PWA_BEACON_EVENT_TYPES = [
  "pwa_connect",
  "frame_tap",
  "confirm_shown",
  "confirm_accept",
  "error",
] as const;

export type PwaBeaconEventType = (typeof PWA_BEACON_EVENT_TYPES)[number];

export type PwaBeaconPayload = {
  type: PwaBeaconEventType;
  venture_id?: string;
  session_id?: string;
  payload?: Record<string, unknown>;
  guardian_status?: string;
  execution_ref?: string;
};

/**
 * Map a UI state-machine event to a PEL beacon type (or null when no emit).
 * confirm_accept is intentional and not driven solely by the reducer — emit
 * from the confirm click/voice path with emitPwaBeacon directly.
 */
export function beaconTypeFromUiEvent(event: UiSessionEvent): PwaBeaconEventType | null {
  switch (event.type) {
    case "CONNECT_OK":
      return "pwa_connect";
    case "FRAME_START":
      return "frame_tap";
    case "CONFIRMATION_REQUIRED":
      return "confirm_shown";
    case "CONNECT_FAIL":
    case "ERROR":
      return "error";
    default:
      return null;
  }
}

/**
 * POST one thin beacon. Never throws. Prefer keepalive fetch so unload still ships.
 */
export function emitPwaBeacon(apiBase: string, body: PwaBeaconPayload): void {
  const base = apiBase.replace(/\/$/, "");
  const url = `${base}/events`;
  const envelope = {
    type: body.type,
    venture_id: body.venture_id || "advoi",
    session_id: body.session_id,
    payload: body.payload || {},
    guardian_status: body.guardian_status,
    execution_ref: body.execution_ref,
  };

  try {
    const json = JSON.stringify(envelope);
    // sendBeacon cannot set Content-Type reliably as application/json on all browsers;
    // keepalive fetch is the preferred path for same-origin /api rewrites.
    if (typeof fetch === "function") {
      void fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: json,
        keepalive: true,
        credentials: "same-origin",
      }).catch(() => {
        /* analytics must not break the shell */
      });
      return;
    }
    if (typeof navigator !== "undefined" && typeof navigator.sendBeacon === "function") {
      navigator.sendBeacon(url, new Blob([json], { type: "application/json" }));
    }
  } catch {
    /* swallow */
  }
}

/**
 * Emit a beacon for a UI state-machine transition when the mapping is non-null.
 */
export function emitBeaconForUiEvent(
  apiBase: string,
  event: UiSessionEvent,
  opts?: {
    session_id?: string;
    payload?: Record<string, unknown>;
    venture_id?: string;
  },
): void {
  const type = beaconTypeFromUiEvent(event);
  if (!type) return;
  emitPwaBeacon(apiBase, {
    type,
    venture_id: opts?.venture_id,
    session_id: opts?.session_id,
    payload: {
      ui_event: event.type,
      ...(opts?.payload || {}),
    },
  });
}
