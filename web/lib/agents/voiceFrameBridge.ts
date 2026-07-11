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

type AgentLastRunRow = {
  id?: string;
  frame_id?: string;
  last_run?: {
    status?: string;
    spoken_summary?: string;
    timestamp?: number | string;
  };
};

function lastRunMs(ts: number | string | undefined | null): number | null {
  if (ts == null || ts === "") return null;
  if (typeof ts === "number") return ts;
  const parsed = Number(ts);
  return Number.isFinite(parsed) ? parsed : null;
}

/** True when agent last_run timestamp is newer than mirror start. */
export function detectVoiceMirrorComplete(
  frameId: string,
  agents: readonly AgentLastRunRow[],
  startedAtMs: number,
): boolean {
  const agent = agents.find((a) => a.frame_id === frameId);
  const runMs = lastRunMs(agent?.last_run?.timestamp);
  if (runMs == null) return false;
  return runMs >= startedAtMs;
}

export type VoiceMirrorResult = {
  frame_id: string;
  agent_id?: string;
  status?: string;
  spoken_summary?: string;
};

export function voiceMirrorResultFromAgent(
  frameId: string,
  agents: readonly AgentLastRunRow[],
): VoiceMirrorResult | null {
  const agent = agents.find((a) => a.frame_id === frameId);
  if (!agent?.last_run) return null;
  return {
    frame_id: frameId,
    agent_id: agent.id,
    status: agent.last_run.status,
    spoken_summary: agent.last_run.spoken_summary,
  };
}