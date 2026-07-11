/**
 * Execute multi-agent slice plans with parallel, wave, or stagger modes.
 */

import {
  chunkFrameWaves,
  mergeOrchestratePayloads,
} from "./agentSlices";
import {
  dispatchSquad,
  runFrameSliceParallel,
  runSingleFrame,
} from "./orchestrateClient";
import type {
  FrameRunResult,
  OrchestratePayload,
  RunExecutionMode,
} from "./types";

export type WaveCallbacks = {
  onWaveStart?: (waveIndex: number, frameIds: string[]) => void;
  onFrameDone?: (frameId: string, result: FrameRunResult) => void;
  onWaveDone?: (waveIndex: number, payload: OrchestratePayload) => void;
};

/** Run frame ids using parallel batches per mode. */
export async function executeSlicePlan(
  frameIds: string[],
  mode: RunExecutionMode,
  callbacks?: WaveCallbacks,
): Promise<OrchestratePayload> {
  const waves = chunkFrameWaves(frameIds, mode);
  const payloads: OrchestratePayload[] = [];

  for (let wi = 0; wi < waves.length; wi++) {
    const wave = waves[wi];
    callbacks?.onWaveStart?.(wi, wave);

    const runOneFrame = async (fid: string): Promise<FrameRunResult> => {
      const row = await runSingleFrame(fid, { refresh: true, confirmed: true });
      const result: FrameRunResult = {
        frame_id: fid,
        status: row.status ?? "ok",
        spoken_summary: row.spoken_summary,
      };
      callbacks?.onFrameDone?.(fid, result);
      return result;
    };

    if (mode === "stagger") {
      const staggerResults: FrameRunResult[] = [];
      for (const fid of wave) {
        staggerResults.push(await runOneFrame(fid));
      }
      const partial: OrchestratePayload = {
        results: staggerResults,
        spoken_summary: staggerResults.map((r) => r.spoken_summary).filter(Boolean).join(" "),
      };
      payloads.push(partial);
      callbacks?.onWaveDone?.(wi, partial);
    } else if (mode === "wave") {
      const waveResults = await Promise.all(wave.map(runOneFrame));
      const partial: OrchestratePayload = {
        results: waveResults,
        spoken_summary: waveResults.map((r) => r.spoken_summary).filter(Boolean).join(" "),
      };
      payloads.push(partial);
      callbacks?.onWaveDone?.(wi, partial);
    } else {
      const payload = await runFrameSliceParallel(wave, { refresh: true });
      payloads.push(payload);
      for (const r of payload.results ?? []) {
        callbacks?.onFrameDone?.(r.frame_id, r);
      }
      callbacks?.onWaveDone?.(wi, payload);
    }
  }

  return mergeOrchestratePayloads(payloads);
}

/** Run squad agent frames then optionally dispatch the squad webhook. */
export async function executeSquadSlicePlan(
  frameIds: string[],
  squadId: string,
  opts: { mode?: RunExecutionMode; dispatchAfter?: boolean } = {},
  callbacks?: WaveCallbacks,
): Promise<OrchestratePayload & { squad_dispatch?: unknown }> {
  const payload = await executeSlicePlan(frameIds, opts.mode ?? "parallel", callbacks);
  if (!opts.dispatchAfter) return payload;
  const dispatch = await dispatchSquad(squadId);
  return { ...payload, squad_dispatch: dispatch };
}