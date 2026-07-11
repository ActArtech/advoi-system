/**
 * Agent slice models for parallel multi-agent UI.
 * Keep Python mirror in tests/test_agent_slices.py in sync.
 */

import type {
  AgentRow,
  AgentSliceModel,
  FrameRow,
  FrameRunResult,
  OrchestratePayload,
  RunExecutionMode,
  SliceResultRow,
  SliceRunPhase,
  SliceRunProgress,
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

/** Relative label for agent.last_run.timestamp (e.g. "just now", "5m ago"). */
export function formatLastRunRelative(ts: string | number | undefined | null): string | undefined {
  if (ts == null || ts === "") return undefined;
  const ms = typeof ts === "number" ? ts : Date.parse(ts);
  if (Number.isNaN(ms)) return undefined;
  const diffMs = Date.now() - ms;
  if (diffMs < 60_000) return "just now";
  const minutes = Math.floor(diffMs / 60_000);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
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
    queuedFrameIds?: Set<string>;
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
  const queued = options?.queuedFrameIds ?? new Set<string>();

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
    else if (queued.has(frameId)) phase = "queued";
    else if (result?.status === "ok" || result?.status === "success") phase = "ok";
    else if (result?.status) phase = result.status === "error" ? "error" : "ok";

    const lastRunTs =
      "last_run" in agent ? agent.last_run?.timestamp : undefined;

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
      lastRunAt: lastRunTs != null ? String(lastRunTs) : undefined,
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

export function waveSizeForMode(mode: RunExecutionMode): number {
  if (mode === "parallel") return 64;
  if (mode === "wave") return 2;
  return 1;
}

/** Split frame ids into execution waves (wave=2, stagger=1, parallel=single wave). */
export function chunkFrameWaves(frameIds: string[], mode: RunExecutionMode): string[][] {
  const size = waveSizeForMode(mode);
  if (frameIds.length === 0) return [];
  if (mode === "parallel") return [frameIds];
  const waves: string[][] = [];
  for (let i = 0; i < frameIds.length; i += size) {
    waves.push(frameIds.slice(i, i + size));
  }
  return waves;
}

/** Resolve frame ids for all agents in a squad. */
export function frameIdsForSquadAgentIds(
  agentIds: string[],
  frames: FrameRow[],
): string[] {
  const byAgent = Object.fromEntries(frames.map((f) => [f.agent_id, f.id]));
  const ids: string[] = [];
  for (const aid of agentIds) {
    const fid = byAgent[aid];
    if (fid) ids.push(fid);
  }
  return ids;
}

export function frameIdsForSquadSlice(
  squad: SquadSliceModel,
  frames: FrameRow[],
): string[] {
  return frameIdsForSquadAgentIds(squad.agentIds, frames);
}

export function runProgressModel(
  mode: RunExecutionMode,
  waveIndex: number,
  waves: string[][],
  completedInCurrentWave: number,
): SliceRunProgress {
  const totalFrames = waves.reduce((n, w) => n + w.length, 0);
  let completedFrames = 0;
  for (let i = 0; i < waveIndex; i++) completedFrames += waves[i].length;
  completedFrames += completedInCurrentWave;
  const percent = totalFrames > 0 ? Math.round((completedFrames / totalFrames) * 100) : 0;
  return {
    mode,
    waveIndex,
    waveCount: waves.length,
    completedFrames,
    totalFrames,
    percent,
  };
}

/** Merge orchestrate payloads from multiple waves. */
export function mergeOrchestratePayloads(
  payloads: OrchestratePayload[],
): OrchestratePayload {
  const results = payloads.flatMap((p) => p.results ?? []);
  const agents_used = [...new Set(payloads.flatMap((p) => p.agents_used ?? []))];
  const systems = [...new Set(payloads.flatMap((p) => p.systems ?? []))];
  const spoken = payloads.map((p) => p.spoken_summary).filter(Boolean).join(" ");
  const lastSquads = payloads.findLast((p) => p.squads)?.squads ?? null;
  return {
    results,
    agents_used,
    systems,
    spoken_summary: spoken,
    squads: lastSquads ?? undefined,
  };
}

function isFailedResultStatus(status?: string): boolean {
  return status === "error" || status === "failed";
}

/** Frame ids whose orchestrate result status is error or failed. */
export function frameIdsFromFailedResults(results: FrameRunResult[]): string[] {
  return results
    .filter((r) => isFailedResultStatus(r.status))
    .map((r) => r.frame_id);
}

export function countFailedResults(results: FrameRunResult[]): number {
  return results.filter((r) => isFailedResultStatus(r.status)).length;
}

export type WavePlanDescription = {
  mode: RunExecutionMode;
  waveCount: number;
  waves: { index: number; frameIds: string[]; labels: string[] }[];
};

/** Human-readable wave batches for preview chips (parallel = one wave). */
export function describeWavePlan(
  frameIds: string[],
  mode: RunExecutionMode,
): WavePlanDescription {
  const waves = chunkFrameWaves(frameIds, mode);
  return {
    mode,
    waveCount: waves.length,
    waves: waves.map((waveFrameIds, index) => ({
      index,
      frameIds: waveFrameIds,
      labels: waveFrameIds.map(shortFrameLabel),
    })),
  };
}

/** Aggregate progress when running multiple squads (frame + squad completion). */
export function squadRunProgressModel(
  completedSquads: number,
  totalSquads: number,
  completedFrames: number,
  totalFrames: number,
): {
  completedSquads: number;
  totalSquads: number;
  completedFrames: number;
  totalFrames: number;
  percent: number;
  squadPercent: number;
} {
  const percent =
    totalFrames > 0 ? Math.round((completedFrames / totalFrames) * 100) : 0;
  const squadPercent =
    totalSquads > 0 ? Math.round((completedSquads / totalSquads) * 100) : 0;
  return {
    completedSquads,
    totalSquads,
    completedFrames,
    totalFrames,
    percent,
    squadPercent,
  };
}

export function buildResultRows(
  slices: AgentSliceModel[],
  results: FrameRunResult[],
): SliceResultRow[] {
  const byFrame = Object.fromEntries(results.map((r) => [r.frame_id, r]));
  return slices
    .filter((s) => byFrame[s.frameId])
    .map((s) => {
      const r = byFrame[s.frameId];
      return {
        frameId: s.frameId,
        agentId: s.agentId,
        shortLabel: s.shortLabel,
        label: s.label,
        status: r.status,
        spokenSummary: r.spoken_summary,
      };
    });
}