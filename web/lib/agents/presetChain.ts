/**
 * Sequential preset chains for multi-wave agent orchestration.
 */

import { presetById, type SlicePreset } from "./slicePresets";
import { mergeOrchestratePayloads } from "./agentSlices";
import type { OrchestratePayload } from "./types";

export type PresetChain = {
  id: string;
  label: string;
  presetIds: readonly string[];
};

export const PRESET_CHAINS: readonly PresetChain[] = [
  {
    id: "ops_then_intel",
    label: "Ops → Intel",
    presetIds: ["ops_core", "intel"],
  },
] as const;

export function chainById(id: string): PresetChain | undefined {
  return PRESET_CHAINS.find((c) => c.id === id);
}

export function resolveChainPresets(chain: PresetChain): SlicePreset[] {
  return chain.presetIds
    .map((id) => presetById(id))
    .filter((p): p is SlicePreset => p != null);
}

export type PresetRunner = (preset: SlicePreset) => Promise<OrchestratePayload>;

/** Run each preset in sequence; merge spoken summaries and results. */
export async function executePresetChain(
  chain: PresetChain,
  runPreset: PresetRunner,
): Promise<OrchestratePayload> {
  const presets = resolveChainPresets(chain);
  if (presets.length === 0) {
    throw new Error(`No presets resolved for chain ${chain.id}`);
  }
  const payloads: OrchestratePayload[] = [];
  for (const preset of presets) {
    payloads.push(await runPreset(preset));
  }
  return mergeOrchestratePayloads(payloads);
}