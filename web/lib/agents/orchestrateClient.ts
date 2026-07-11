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
  opts: { dispatchSquads?: boolean; refresh?: boolean } = {},
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
  });
  if (!res.ok) throw new Error(`run-six ${res.status}`);
  return res.json();
}

export async function runFrameSliceParallel(
  frameIds: string[],
  opts: { refresh?: boolean } = {},
  base = apiBaseUrl(),
): Promise<OrchestratePayload> {
  const res = await fetch(`${base}/agents/orchestrate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      frame_ids: frameIds,
      confirmed: true,
      refresh: opts.refresh ?? true,
    }),
  });
  if (!res.ok) throw new Error(`orchestrate ${res.status}`);
  return res.json();
}

export async function runSingleFrame(
  frameId: string,
  opts: { confirmed?: boolean; refresh?: boolean } = {},
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
  });
  if (!res.ok) throw new Error(`frame ${frameId} ${res.status}`);
  return res.json();
}