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
  /** Dispatch all squads after the chain completes */
  dispatchAfter?: boolean;
};

export const PRESET_CHAINS: readonly PresetChain[] = [
  {
    id: "ops_then_intel",
    label: "Ops → Intel",
    presetIds: ["ops_core", "intel"],
  },
  {
    id: "morning_then_ops",
    label: "Pulse → Ops",
    presetIds: ["morning_pulse", "ops_core"],
  },
  {
    id: "morning_then_full",
    label: "Pulse → Full 6",
    presetIds: ["morning_pulse", "full_six"],
  },
  {
    id: "intel_then_dispatch",
    label: "Intel → Dispatch",
    presetIds: ["intel"],
    dispatchAfter: true,
  },
  {
    id: "full_six_then_dispatch",
    label: "Full 6 → Dispatch",
    presetIds: ["full_six"],
    dispatchAfter: true,
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

export type ChainDispatchRunner = () => Promise<OrchestratePayload>;

/** Run each preset in sequence; merge spoken summaries and results. */
export async function executePresetChain(
  chain: PresetChain,
  runPreset: PresetRunner,
  dispatchAfter?: ChainDispatchRunner,
): Promise<OrchestratePayload> {
  const presets = resolveChainPresets(chain);
  if (presets.length === 0) {
    throw new Error(`No presets resolved for chain ${chain.id}`);
  }
  const payloads: OrchestratePayload[] = [];
  for (const preset of presets) {
    payloads.push(await runPreset(preset));
  }
  let merged = mergeOrchestratePayloads(payloads);
  if (chain.dispatchAfter && dispatchAfter) {
    const dispatchPayload = await dispatchAfter();
    merged = mergeOrchestratePayloads([merged, dispatchPayload]);
  }
  return merged;
}