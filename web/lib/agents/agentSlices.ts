/**
 * Agent slice models for parallel multi-agent UI.
 * Keep Python mirror in tests/test_agent_slices.py in sync.
 */

import type {
  AgentRow,
  AgentSliceModel,
  FrameRow,
  FrameRunResult,
  SliceRunPhase,
  SquadRow,
  SquadSliceModel,
} from "./types";

export const FRAME_SHORT: Record<string, string> = {
  fleet_status: "fleet",
  open_briefs: "briefs",
  queue_deep_review: "review",
  systems_pulse: "pulse",
  memory_health: "memory",
  guardian_status: "guardian",
};

export const DEFAULT_SIX_FRAME_IDS = [
  "fleet_status",
  "open_briefs",
  "queue_deep_review",
  "systems_pulse",
  "memory_health",
  "guardian_status",
] as const;

export function shortFrameLabel(frameId: string): string {
  return FRAME_SHORT[frameId] ?? frameId.replace(/_/g, " ").slice(0, 8);
}

export function buildSquadSlices(
  squads: SquadRow[],
  agents: AgentRow[],
): SquadSliceModel[] {
  const warm = new Set(agents.filter((a) => a.cached).map((a) => a.id));
  return squads.map((s) => ({
    squadId: s.id,
    name: s.name,
    channel: s.channel,
    ventureId: s.venture_id,
    agentIds: s.agent_ids,
    warmCount: s.agent_ids.filter((id) => warm.has(id)).length,
    total: s.agent_ids.length,
  }));
}

export function buildAgentSlices(
  agents: AgentRow[],
  frames: FrameRow[],
  options?: {
    selectedIds?: Set<string>;
    runningFrameIds?: Set<string>;
    results?: FrameRunResult[];
    squadByAgent?: Map<string, string[]>;
  },
): AgentSliceModel[] {
  const frameByAgent = Object.fromEntries(
    frames.map((f) => [f.agent_id, f]),
  );
  const resultByFrame = Object.fromEntries(
    (options?.results ?? []).map((r) => [r.frame_id, r]),
  );
  const selected = options?.selectedIds ?? new Set<string>();
  const running = options?.runningFrameIds ?? new Set<string>();

  const ordered = agents.length
    ? agents
    : frames.map((f) => ({
        id: f.agent_id,
        name: f.agent_name,
        frame_id: f.id,
        cached: false,
      }));

  return ordered.map((agent) => {
    const frame = frameByAgent[agent.id] ?? frames.find((f) => f.id === agent.frame_id);
    const frameId = frame?.id ?? agent.frame_id ?? agent.id;
    const result = resultByFrame[frameId];
    let phase: SliceRunPhase = "idle";
    if (running.has(frameId)) phase = "running";
    else if (result?.status === "ok" || result?.status === "success") phase = "ok";
    else if (result?.status) phase = result.status === "error" ? "error" : "ok";

    return {
      agentId: agent.id,
      frameId,
      label: frame?.label ?? agent.name ?? agent.id,
      shortLabel: shortFrameLabel(frameId),
      warm: Boolean(agent.cached),
      phase,
      lastStatus:
        result?.status ??
        ("last_run" in agent ? agent.last_run?.status : undefined),
      selected: selected.has(agent.id),
      squadIds: options?.squadByAgent?.get(agent.id) ?? [],
    };
  });
}

/** Map each agent id to squad ids that include it. */
export function squadMembershipMap(squads: SquadRow[]): Map<string, string[]> {
  const map = new Map<string, string[]>();
  for (const squad of squads) {
    for (const aid of squad.agent_ids) {
      const list = map.get(aid) ?? [];
      list.push(squad.id);
      map.set(aid, list);
    }
  }
  return map;
}

/** Frame ids for selected agent slices (parallel orchestrate). */
export function frameIdsFromSelectedSlices(slices: AgentSliceModel[]): string[] {
  return slices.filter((s) => s.selected).map((s) => s.frameId);
}

/** All six default frame ids when nothing selected. */
export function resolveOrchestrateFrameIds(
  slices: AgentSliceModel[],
  mode: "selected" | "all_six",
): string[] {
  if (mode === "all_six") return [...DEFAULT_SIX_FRAME_IDS];
  const picked = frameIdsFromSelectedSlices(slices);
  return picked.length > 0 ? picked : [...DEFAULT_SIX_FRAME_IDS];
}

export function countSlicesByPhase(slices: AgentSliceModel[]): Record<SliceRunPhase, number> {
  const counts: Record<SliceRunPhase, number> = {
    idle: 0,
    queued: 0,
    running: 0,
    ok: 0,
    error: 0,
  };
  for (const s of slices) counts[s.phase] += 1;
  return counts;
}

export function squadWarmLabel(squad: SquadSliceModel): string {
  return `${squad.warmCount}/${squad.total} warm`;
}