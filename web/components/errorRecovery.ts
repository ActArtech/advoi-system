/**
 * PWA error recovery paths — pure model for VoiceSession error state.
 *
 * Paths:
 * 1. mic_denied — clear message + retry (re-request mic / Connect)
 * 2. livekit_connect — retry + Path C fallback (`/voice-server`)
 * 3. api_frame — retry + Path C (502 / frame / API failures)
 *
 * Wired to UI state `error` and PEL beacon type `error`.
 * Keep Python mirror in tests/test_error_recovery.py in sync.
 */

export const PATH_C_HREF = "/voice-server";
export const PATH_C_LABEL = "Server voice (Path C)";

export type RecoveryKind = "mic_denied" | "livekit_connect" | "api_frame" | "generic";

export type ErrorRecoveryInput = {
  kind: RecoveryKind;
  /** Raw error / status text for detail line. */
  detail?: string | null;
  /** HTTP status when known (api_frame / token). */
  status?: number | null;
  /** Frame or action id for retry context. */
  target?: string | null;
};

export type ErrorRecoveryModel = {
  kind: RecoveryKind;
  title: string;
  message: string;
  showRetry: boolean;
  retryLabel: string;
  showPathC: boolean;
  pathCHref: string;
  pathCLabel: string;
  /** Optional HTTP status for tests / data attributes. */
  status: number | null;
  target: string | null;
};

const MIC_PATTERNS = [
  /notallowed/i,
  /permissiondenied/i,
  /permission denied/i,
  /microphone.*(block|den|permission|support)/i,
  /mic.*(block|den|permission)/i,
  /does not support microphone/i,
  /getusermedia/i,
  /notreadableerror/i,
  /securityerror/i,
];

/**
 * Classify a connect-time failure (getUserMedia, token, LiveKit room.connect).
 */
export function classifyConnectError(
  err: unknown,
  opts?: { httpStatus?: number | null },
): ErrorRecoveryInput {
  const message = err instanceof Error ? err.message : String(err ?? "Connection failed");
  const name = err instanceof Error ? err.name : "";
  const status = opts?.httpStatus ?? extractHttpStatus(message);

  const blob = `${name} ${message}`;
  if (MIC_PATTERNS.some((re) => re.test(blob)) || /microphone is blocked/i.test(message)) {
    return { kind: "mic_denied", detail: message, status };
  }

  // Token / LiveKit transport failures
  return {
    kind: "livekit_connect",
    detail: message,
    status,
  };
}

/**
 * Classify an API / frame / intent failure (including HTTP 502).
 */
export function classifyApiError(
  err: unknown,
  opts?: { httpStatus?: number | null; target?: string | null },
): ErrorRecoveryInput {
  const message = err instanceof Error ? err.message : String(err ?? "Request failed");
  const status = opts?.httpStatus ?? extractHttpStatus(message);
  return {
    kind: "api_frame",
    detail: message,
    status,
    target: opts?.target ?? null,
  };
}

/** Pull trailing or embedded HTTP status codes from thrown messages. */
export function extractHttpStatus(message: string): number | null {
  const m =
    message.match(/\b(?:returned|HTTP|status)\s*(\d{3})\b/i) ||
    message.match(/\b([45]\d{2})\b/);
  if (!m) return null;
  const n = Number(m[1]);
  return Number.isFinite(n) ? n : null;
}

/**
 * Build the recovery panel presentation for the error state.
 * Never throws — unknown kinds fall back to a generic retry path.
 */
export function errorRecoveryModel(input: ErrorRecoveryInput): ErrorRecoveryModel {
  const detail = (input.detail || "").trim();
  const status = input.status ?? null;
  const target = input.target ?? null;

  switch (input.kind) {
    case "mic_denied":
      return {
        kind: "mic_denied",
        title: "Microphone blocked",
        message:
          detail && /block|den|permission|notallowed/i.test(detail)
            ? "Microphone access was denied. Allow the mic for this site in browser settings, then tap Retry."
            : detail ||
              "Microphone access was denied. Allow the mic for this site, then tap Retry.",
        showRetry: true,
        retryLabel: "Retry connect",
        showPathC: false,
        pathCHref: PATH_C_HREF,
        pathCLabel: PATH_C_LABEL,
        status,
        target,
      };

    case "livekit_connect": {
      const statusHint =
        status === 401 || status === 403 || status === 503
          ? ` Token endpoint returned ${status}.`
          : status
            ? ` (HTTP ${status}).`
            : "";
      return {
        kind: "livekit_connect",
        title: "Voice connect failed",
        message:
          (detail
            ? detail
            : "Could not connect to LiveKit voice.") +
          statusHint +
          " Retry, or use server voice without LiveKit.",
        showRetry: true,
        retryLabel: "Retry connect",
        showPathC: true,
        pathCHref: PATH_C_HREF,
        pathCLabel: PATH_C_LABEL,
        status,
        target,
      };
    }

    case "api_frame": {
      const is502 = status === 502 || /\b502\b/.test(detail);
      const statusPart =
        status != null ? ` API returned ${status}.` : is502 ? " API returned 502." : "";
      return {
        kind: "api_frame",
        title: is502 || (status != null && status >= 500) ? "Service unavailable" : "Request failed",
        message:
          (detail || "Frame or API request failed.") +
          statusPart +
          " Retry, or switch to server voice (Path C).",
        showRetry: true,
        retryLabel: target ? "Retry request" : "Retry",
        showPathC: true,
        pathCHref: PATH_C_HREF,
        pathCLabel: PATH_C_LABEL,
        status,
        target,
      };
    }

    default:
      return {
        kind: "generic",
        title: "Something went wrong",
        message: detail || "An unexpected error occurred. You can retry.",
        showRetry: true,
        retryLabel: "Retry",
        showPathC: true,
        pathCHref: PATH_C_HREF,
        pathCLabel: PATH_C_LABEL,
        status,
        target,
      };
  }
}

/** Beacon payload fragment for PEL `error` events. */
export function recoveryBeaconPayload(model: ErrorRecoveryModel): Record<string, unknown> {
  return {
    recovery_kind: model.kind,
    message: model.message,
    status: model.status,
    target: model.target,
  };
}
