/**
 * Dispatch squads tied to an agent without re-running frames.
 */

import type { SquadRow } from "./types";
import { dispatchSquad } from "./orchestrateClient";
import { mergeOrchestratePayloads } from "./agentSlices";
import type { OrchestratePayload } from "./types";

export function squadIdsForAgent(agentId: string, squads: SquadRow[]): string[] {
  return squads.filter((s) => s.agent_ids.includes(agentId)).map((s) => s.id);
}

export async function dispatchSquadsForAgent(
  agentId: string,
  squads: SquadRow[],
  opts: { signal?: AbortSignal } = {},
): Promise<OrchestratePayload> {
  const ids = squadIdsForAgent(agentId, squads);
  if (ids.length === 0) {
    return { spoken_summary: "No squads for this agent", results: [] };
  }
  const payloads: OrchestratePayload[] = [];
  for (const squadId of ids) {
    if (opts.signal?.aborted) throw new DOMException("Aborted", "AbortError");
    const res = await dispatchSquad(squadId, { signal: opts.signal });
    payloads.push({
      spoken_summary: res.spoken_summary,
      results: [],
      squads: { dispatched: 1, total: 1 },
    });
  }
  const merged = mergeOrchestratePayloads(payloads);
  return {
    ...merged,
    squads: { dispatched: ids.length, total: ids.length },
  };
}