export type AgentRow = {
  id: string;
  name?: string;
  cached?: boolean;
  frame_id?: string;
  last_run?: {
    status?: string;
    spoken_summary?: string;
    timestamp?: number | string;
  };
};

export type FrameRow = {
  id: string;
  label: string;
  agent_id: string;
  agent_name?: string;
  requires_confirmation?: boolean;
};

export type SquadRow = {
  id: string;
  name: string;
  channel: string;
  agent_ids: string[];
  venture_id: string;
};

export type FrameRunResult = {
  frame_id: string;
  agent_id?: string;
  status?: string;
  spoken_summary?: string;
};

export type OrchestratePayload = {
  results?: FrameRunResult[];
  agents_used?: string[];
  systems?: string[];
  spoken_summary?: string;
  squads?: { dispatched?: number; total?: number } | null;
};

export type SliceRunPhase = "idle" | "queued" | "running" | "ok" | "error";

export type AgentSliceModel = {
  agentId: string;
  frameId: string;
  label: string;
  shortLabel: string;
  warm: boolean;
  phase: SliceRunPhase;
  lastStatus?: string;
  selected: boolean;
  squadIds: string[];
};

export type SquadSliceModel = {
  squadId: string;
  name: string;
  channel: string;
  ventureId: string;
  agentIds: string[];
  warmCount: number;
  total: number;
};

/** parallel = all at once; wave = batches of 2; stagger = one-by-one */
export type RunExecutionMode = "parallel" | "wave" | "stagger";

export type SliceRunProgress = {
  mode: RunExecutionMode;
  waveIndex: number;
  waveCount: number;
  completedFrames: number;
  totalFrames: number;
  percent: number;
};

export type SquadRunProgress = SliceRunProgress & {
  squadId: string;
};

export type SliceResultRow = {
  frameId: string;
  agentId?: string;
  shortLabel: string;
  label: string;
  status?: string;
  spokenSummary?: string;
};