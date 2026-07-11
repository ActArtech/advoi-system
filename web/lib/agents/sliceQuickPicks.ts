/**
 * One-tap multi-select groups for the Agents slice grid.
 * Keep Python mirror in tests/test_agent_slices.py in sync.
 */

import type { AgentSliceModel } from "./types";
import { presetById } from "./slicePresets";
import { DEFAULT_SIX_FRAME_IDS } from "./agentSlices";

export type SliceQuickPickAction = "all" | "clear";

export type SliceQuickPick = {
  id: string;
  label: string;
  presetId?: string;
  action?: SliceQuickPickAction;
};

export const SLICE_QUICK_PICKS: readonly SliceQuickPick[] = [
  { id: "all", label: "All 6", action: "all" },
  { id: "ops", label: "Ops", presetId: "ops_core" },
  { id: "intel", label: "Intel", presetId: "intel" },
  { id: "pulse", label: "Pulse", presetId: "morning_pulse" },
  { id: "clear", label: "Clear", action: "clear" },
] as const;

export function quickPickById(id: string): SliceQuickPick | undefined {
  return SLICE_QUICK_PICKS.find((p) => p.id === id);
}

/** Map frame ids to agent ids present in the current slice grid. */
export function agentIdsForFrameIds(
  frameIds: readonly string[],
  slices: readonly AgentSliceModel[],
): string[] {
  const wanted = new Set(frameIds);
  return slices.filter((s) => wanted.has(s.frameId)).map((s) => s.agentId);
}

/** Resolve agent ids for a quick-pick chip. */
export function agentIdsForQuickPick(
  pick: SliceQuickPick,
  slices: readonly AgentSliceModel[],
): string[] {
  if (pick.action === "clear") return [];
  if (pick.action === "all") return agentIdsForFrameIds(DEFAULT_SIX_FRAME_IDS, slices);
  if (pick.presetId) {
    const preset = presetById(pick.presetId);
    if (!preset) return [];
    return agentIdsForFrameIds(preset.frameIds, slices);
  }
  return [];
}