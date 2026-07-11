/**
 * Curated slice run presets for the Agents orchestrator.
 * Keep Python mirror in tests/test_agent_slices.py in sync.
 */

import { DEFAULT_SIX_FRAME_IDS } from "./agentSlices";
import type { RunExecutionMode } from "./types";

export type SlicePreset = {
  id: string;
  label: string;
  description?: string;
  frameIds: readonly string[];
  mode: RunExecutionMode;
};

export const SLICE_PRESETS: readonly SlicePreset[] = [
  {
    id: "morning_pulse",
    label: "Morning pulse",
    description: "Systems pulse only, one at a time",
    frameIds: ["systems_pulse"],
    mode: "stagger",
  },
  {
    id: "ops_core",
    label: "Ops core",
    description: "Fleet, briefs, guardian in waves of two",
    frameIds: ["fleet_status", "open_briefs", "guardian_status"],
    mode: "wave",
  },
  {
    id: "intel",
    label: "Intel",
    description: "Briefs, deep review, memory in waves of two",
    frameIds: ["open_briefs", "queue_deep_review", "memory_health"],
    mode: "wave",
  },
  {
    id: "full_six",
    label: "Full six",
    description: "All default frames in parallel",
    frameIds: DEFAULT_SIX_FRAME_IDS,
    mode: "parallel",
  },
] as const;

export function presetById(id: string): SlicePreset | undefined {
  return SLICE_PRESETS.find((p) => p.id === id);
}

/** Built-in + user presets for the presets bar (user entries last). */
export function allPresetsForBar(
  userPresets: readonly SlicePreset[] = [],
): readonly SlicePreset[] {
  return [...SLICE_PRESETS, ...userPresets];
}