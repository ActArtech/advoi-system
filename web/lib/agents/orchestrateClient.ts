import type { AgentRow, FrameRow, OrchestratePayload, SquadRow } from "./types";

const defaultBase =
  typeof process !== "undefined"
    ? process.env.NEXT_PUBLIC_ADVOI_API_URL?.replace(/\/$/, "") || "/api"
    : "/api";

export function apiBaseUrl(override?: string): string {
  return override?.replace(/\/$/, "") || defaultBase;
}

export async function fetchAgents(base = apiBaseUrl()): Promise<AgentRow[]> {
  const res = await fetch(`${base}/agents`);
  if (!res.ok) throw new Error(`agents ${res.status}`);
  const data = await res.json();
  return data.agents ?? [];
}

export async function fetchFrames(base = apiBaseUrl()): Promise<FrameRow[]> {
  const res = await fetch(`${base}/frames`);
  if (!res.ok) throw new Error(`frames ${res.status}`);
  const data = await res.json();
  return data.frames ?? [];
}

export async function fetchSquads(base = apiBaseUrl()): Promise<SquadRow[]> {
  const res = await fetch(`${base}/squads`);
  if (!res.ok) throw new Error(`squads ${res.status}`);
  const data = await res.json();
  return data.squads ?? [];
}

export async function runSixParallel(
  opts: { dispatchSquads?: boolean; refresh?: boolean; signal?: AbortSignal } = {},
  base = apiBaseUrl(),
): Promise<OrchestratePayload> {
  const qs = new URLSearchParams({
    refresh: String(opts.refresh ?? true),
    confirmed: "true",
    ...(opts.dispatchSquads ? { dispatch_squads: "true" } : {}),
  });
  const res = await fetch(`${base}/agents/run-six?${qs}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}",
    signal: opts.signal,
  });
  if (!res.ok) throw new Error(`run-six ${res.status}`);
  return res.json();
}

export type SliceOrchestrateBody = {
  frame_ids?: string[];
  mode?: "parallel" | "wave" | "stagger";
  preset_id?: string;
  chain_id?: string;
  dispatch_squads?: boolean;
  confirmed?: boolean;
  refresh?: boolean;
};

export type SliceOrchestratePayload = OrchestratePayload & {
  mode?: string;
  wave_plan?: unknown;
  fail_count?: number;
  preset_id?: string | null;
  chain_id?: string | null;
};

export async function runSliceOrchestrate(
  body: SliceOrchestrateBody,
  opts: { signal?: AbortSignal } = {},
  base = apiBaseUrl(),
): Promise<SliceOrchestratePayload> {
  const res = await fetch(`${base}/agents/orchestrate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      confirmed: true,
      refresh: true,
      ...body,
    }),
    signal: opts.signal,
  });
  if (!res.ok) throw new Error(`orchestrate ${res.status}`);
  return res.json();
}

export async function fetchSliceCatalog(base = apiBaseUrl()): Promise<{
  presets: { id: string; label: string; frameIds: string[]; mode: string }[];
  chains: {
    id: string;
    label: string;
    presetIds: string[];
    dispatchAfter?: boolean;
  }[];
  defaultSix: string[];
}> {
  const res = await fetch(`${base}/agents/slice-catalog`);
  if (!res.ok) throw new Error(`slice-catalog ${res.status}`);
  return res.json();
}

export async function runFrameSliceParallel(
  frameIds: string[],
  opts: { refresh?: boolean; signal?: AbortSignal; mode?: "parallel" | "wave" | "stagger" } = {},
  base = apiBaseUrl(),
): Promise<OrchestratePayload> {
  return runSliceOrchestrate(
    {
      frame_ids: frameIds,
      mode: opts.mode ?? "parallel",
      refresh: opts.refresh ?? true,
      confirmed: true,
    },
    { signal: opts.signal },
    base,
  );
}

export async function runSingleFrame(
  frameId: string,
  opts: { confirmed?: boolean; refresh?: boolean; signal?: AbortSignal } = {},
  base = apiBaseUrl(),
): Promise<{ spoken_summary?: string; status?: string }> {
  const qs = new URLSearchParams({
    ...(opts.refresh ? { refresh: "true" } : {}),
    ...(opts.confirmed ? { confirmed: "true" } : {}),
  });
  const suffix = qs.size ? `?${qs}` : "";
  const res = await fetch(`${base}/frames/${frameId}/run${suffix}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}",
    signal: opts.signal,
  });
  if (!res.ok) throw new Error(`frame ${frameId} ${res.status}`);
  return res.json();
}

export async function dispatchSquad(
  squadId: string,
  opts: { signal?: AbortSignal } = {},
  base = apiBaseUrl(),
): Promise<{ ok?: boolean; spoken_summary?: string; squad_id?: string }> {
  const res = await fetch(`${base}/squads/dispatch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ squad_id: squadId, confirmed: true }),
    signal: opts.signal,
  });
  if (!res.ok) throw new Error(`squad dispatch ${res.status}`);
  return res.json();
}

export async function dispatchAllSquads(
  opts: { signal?: AbortSignal; confirmed?: boolean } = {},
  base = apiBaseUrl(),
): Promise<OrchestratePayload> {
  const qs = new URLSearchParams({ confirmed: String(opts.confirmed ?? true) });
  const res = await fetch(`${base}/squads/dispatch-all?${qs}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}",
    signal: opts.signal,
  });
  if (!res.ok) throw new Error(`dispatch-all ${res.status}`);
  return res.json();
}