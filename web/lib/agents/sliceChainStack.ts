/**
 * Stack preset chain stages into the FIFO run queue.
 */

import type { UserPresetChain } from "./customUserChains";
import { resolveUserChainPresets } from "./customUserChains";
import { chainPlaylistLabels } from "./slicePostRunSuggestions";
import { chainById, resolveChainPresets, type PresetChain } from "./presetChain";
import type { SlicePreset } from "./slicePresets";

export type ChainStackStage = {
  label: string;
  preset: SlicePreset;
};

export type ResolvedChainPlan = {
  chainLabel: string;
  stages: ChainStackStage[];
  dispatchAfter: boolean;
};

export function resolveBuiltinChainPlan(chainId: string): ResolvedChainPlan | null {
  const chain = chainById(chainId);
  if (!chain) return null;
  return resolveChainPlan(chain);
}

export function resolveUserChainPlan(
  chain: UserPresetChain,
  userPresets: readonly SlicePreset[],
): ResolvedChainPlan | null {
  const presets = resolveUserChainPresets(chain, userPresets);
  if (presets.length === 0) return null;
  return {
    chainLabel: chain.label,
    stages: presets.map((preset) => ({
      label: preset.label,
      preset,
    })),
    dispatchAfter: Boolean(chain.dispatchAfter),
  };
}

export function resolveChainPlan(chain: PresetChain): ResolvedChainPlan | null {
  const presets = resolveChainPresets(chain);
  if (presets.length === 0) return null;
  return {
    chainLabel: chain.label,
    stages: presets.map((preset) => ({
      label: preset.label,
      preset,
    })),
    dispatchAfter: Boolean(chain.dispatchAfter),
  };
}

export function labelsForChainPlan(plan: ResolvedChainPlan): string[] {
  return chainPlaylistLabels(
    plan.chainLabel,
    plan.stages.map((s) => s.label),
    plan.dispatchAfter,
  );
}