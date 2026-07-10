/**
 * PWA confirm parity — identical Guardian confirm copy for voice + tap paths.
 *
 * When Guardian returns `confirmation_required`, voice TTS, status line, and
 * the visible Confirm panel all use the same string. Wired to UI state
 * `confirm_pending` and PEL beacons `confirm_shown` / `confirm_accept`.
 *
 * Keep Python mirror in tests/test_confirm_parity.py in sync.
 */

export const DEFAULT_CONFIRM_COPY =
  "Confirm yes on voice or tap Confirm to proceed.";

export const CONFIRM_BUTTON_LABEL = "Confirm";

export const CONFIRM_BANNER_TITLE = "Confirmation required";

export type ConfirmTargetKind = "frame" | "fleet" | "operator";

/** Fields any confirmation_required API response may carry. */
export type ConfirmCopySource = {
  prompt?: string | null;
  spoken_summary?: string | null;
  spoken?: string | null;
};

export type ConfirmParityInput = ConfirmCopySource & {
  targetKind: ConfirmTargetKind;
  /** frame_id, fleet action, or operator id */
  targetId: string;
  /**
   * Optional transcript to re-submit on Confirm for operator/voice paths
   * (e.g. "stop agents confirm"). Frames/fleet use confirmed:true instead.
   */
  acceptTranscript?: string | null;
};

export type ConfirmParityModel = {
  /** Single source of truth: voice TTS + status + banner body. */
  copy: string;
  buttonLabel: string;
  title: string;
  targetKind: ConfirmTargetKind;
  targetId: string;
  acceptTranscript: string | null;
};

/**
 * Normalize Guardian confirmation copy so voice and tap show identical text.
 *
 * Preference order (first non-empty wins):
 * 1. `prompt` — explicit Guardian gate field (fleet, ingestion)
 * 2. `spoken_summary` — frame run API
 * 3. `spoken` — voice intent / respond
 * 4. default
 */
export function confirmCopyFromResponse(data: ConfirmCopySource): string {
  for (const key of ["prompt", "spoken_summary", "spoken"] as const) {
    const raw = data[key];
    if (typeof raw === "string") {
      const trimmed = raw.replace(/\u2014/g, "-").trim();
      if (trimmed) return trimmed;
    }
  }
  return DEFAULT_CONFIRM_COPY;
}

/**
 * Build the confirm panel model from a Guardian confirmation_required payload.
 * Never throws — empty inputs yield the default copy.
 */
export function confirmParityModel(input: ConfirmParityInput): ConfirmParityModel {
  return {
    copy: confirmCopyFromResponse(input),
    buttonLabel: CONFIRM_BUTTON_LABEL,
    title: CONFIRM_BANNER_TITLE,
    targetKind: input.targetKind,
    targetId: input.targetId,
    acceptTranscript:
      typeof input.acceptTranscript === "string" && input.acceptTranscript.trim()
        ? input.acceptTranscript.trim()
        : null,
  };
}

/**
 * Voice and tap must present the same string (strict parity check for tests).
 */
export function assertConfirmCopyParity(spoken: string, displayed: string): boolean {
  return spoken.trim() === displayed.trim();
}
