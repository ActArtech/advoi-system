/**
 * Cross-tab bridge: Voice/home CTAs own API execution; Agents mirrors visuals.
 * Keep Python mirror in tests/test_agent_slices.py in sync.
 */

import { MORNING_PULSE_FRAME_ID } from "@/components/pwaOnboarding";

export type RunFrameDetail = {
  frameId?: string;
  refresh?: boolean;
  source?: string;
};

/** Voice and home surfaces run frames; Agents must not duplicate orchestrate calls. */
export function shouldMirrorVoiceFrame(detail: RunFrameDetail | null | undefined): boolean {
  if (!detail?.frameId) return false;
  if (detail.source === "agents_orchestrator") return false;
  return true;
}

/** Map external frame events to a friendly status label. */
export function voiceMirrorStatusLabel(detail: RunFrameDetail): string {
  const short = detail.frameId === MORNING_PULSE_FRAME_ID ? "morning pulse" : detail.frameId ?? "slice";
  const source = detail.source?.replace(/_/g, " ") ?? "voice";
  return `Syncing ${short} (${source})...`;
}

/** Preset id Agents would use if it owned execution (for tests / future routing). */
export function frameIdToPresetId(frameId: string): string | null {
  if (frameId === MORNING_PULSE_FRAME_ID) return "morning_pulse";
  return null;
}