/**
 * Suggest next multi-agent batches after a slice run completes.
 * Keep Python mirror in tests/test_agent_slices.py in sync.
 */

import { chainById } from "./presetChain";
import { presetById } from "./slicePresets";

export type SliceFollowUpAction =
  | { kind: "run_chain"; chainId: string }
  | { kind: "stack_chain"; chainId: string }
  | { kind: "retry_stagger" };

export type SliceFollowUp = {
  id: string;
  label: string;
  action: SliceFollowUpAction;
};

function frameSetsEqual(a: readonly string[], b: readonly string[]): boolean {
  if (a.length !== b.length) return false;
  const setA = new Set(a);
  return b.every((id) => setA.has(id));
}

function chainFollowUp(chainId: string, stack = false): SliceFollowUp | null {
  const chain = chainById(chainId);
  if (!chain) return null;
  return {
    id: stack ? `stack_${chainId}` : `run_${chainId}`,
    label: stack ? `Stack ${chain.label}` : chain.label,
    action: stack
      ? { kind: "stack_chain", chainId }
      : { kind: "run_chain", chainId },
  };
}

/** Follow-up chips after a batch finishes (or on partial failure). */
export function postRunFollowUps(
  frameIds: readonly string[],
  failCount: number,
): SliceFollowUp[] {
  if (failCount > 0) {
    return [
      {
        id: "retry_stagger",
        label: "Retry failed (stagger)",
        action: { kind: "retry_stagger" },
      },
    ];
  }
  if (frameIds.length === 0) return [];

  const morning = presetById("morning_pulse");
  if (morning && frameSetsEqual(frameIds, morning.frameIds)) {
    return (
      [
        chainFollowUp("morning_then_ops"),
        chainFollowUp("morning_then_full"),
        chainFollowUp("morning_then_ops", true),
      ] as (SliceFollowUp | null)[]
    ).filter((x): x is SliceFollowUp => x != null);
  }

  const ops = presetById("ops_core");
  if (ops && frameSetsEqual(frameIds, ops.frameIds)) {
    return (
      [chainFollowUp("ops_then_intel"), chainFollowUp("ops_then_intel", true)] as (
        | SliceFollowUp
        | null
      )[]
    ).filter((x): x is SliceFollowUp => x != null);
  }

  const intel = presetById("intel");
  if (intel && frameSetsEqual(frameIds, intel.frameIds)) {
    const next = chainFollowUp("intel_then_dispatch");
    return next ? [next] : [];
  }

  const full = presetById("full_six");
  if (full && frameSetsEqual(frameIds, full.frameIds)) {
    const next = chainFollowUp("full_six_then_dispatch");
    return next ? [next] : [];
  }

  return [];
}

/** Labels for each stage when stacking a preset chain into the run queue. */
export function chainPlaylistLabels(
  chainLabel: string,
  presetLabels: readonly string[],
  dispatchAfter?: boolean,
): string[] {
  const labels = presetLabels.map((preset) => `${chainLabel}: ${preset}`);
  if (dispatchAfter) labels.push(`${chainLabel}: Dispatch`);
  return labels;
}