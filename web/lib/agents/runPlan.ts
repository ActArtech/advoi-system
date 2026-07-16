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
  runSliceOrchestrate,
} from "./orchestrateClient";
import type {
  FrameRunResult,
  OrchestratePayload,
  RunExecutionMode,
} from "./types";

export type RunPlanOptions = {
  signal?: AbortSignal;
};

export type WaveCallbacks = {
  onWaveStart?: (waveIndex: number, frameIds: string[]) => void;
  onFrameDone?: (frameId: string, result: FrameRunResult) => void;
  onWaveDone?: (waveIndex: number, payload: OrchestratePayload) => void;
};

export type AllSquadsCallbacks = {
  onSquadStart?: (squadId: string, frameIds: string[]) => void;
  onSquadDone?: (squadId: string, payload: OrchestratePayload) => void;
  onSquadFrameDone?: (squadId: string, frameId: string, result: FrameRunResult) => void;
};

function assertNotAborted(signal?: AbortSignal): void {
  if (signal?.aborted) throw new DOMException("Aborted", "AbortError");
}

function useServerSlicePath(mode: RunExecutionMode, callbacks?: WaveCallbacks): boolean {
  if (mode === "stagger") return false;
  if (!callbacks) return true;
  return !callbacks.onFrameDone && !callbacks.onWaveStart && !callbacks.onWaveDone;
}

/** Run frame ids using parallel batches per mode. */
export async function executeSlicePlan(
  frameIds: string[],
  mode: RunExecutionMode,
  callbacks?: WaveCallbacks,
  opts?: RunPlanOptions,
): Promise<OrchestratePayload> {
  const signal = opts?.signal;
  if (useServerSlicePath(mode, callbacks)) {
    assertNotAborted(signal);
    return runSliceOrchestrate(
      { frame_ids: frameIds, mode, refresh: true, confirmed: true },
      { signal },
    );
  }

  const waves = chunkFrameWaves(frameIds, mode);
  const payloads: OrchestratePayload[] = [];

  for (let wi = 0; wi < waves.length; wi++) {
    assertNotAborted(signal);
    const wave = waves[wi];
    callbacks?.onWaveStart?.(wi, wave);

    const runOneFrame = async (fid: string): Promise<FrameRunResult> => {
      assertNotAborted(signal);
      try {
        const row = await runSingleFrame(fid, {
          refresh: true,
          confirmed: true,
          signal,
        });
        const result: FrameRunResult = {
          frame_id: fid,
          status: row.status ?? "ok",
          spoken_summary: row.spoken_summary,
        };
        callbacks?.onFrameDone?.(fid, result);
        return result;
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") throw err;
        const message = err instanceof Error ? err.message : String(err);
        const result: FrameRunResult = {
          frame_id: fid,
          status: "error",
          spoken_summary: message,
        };
        callbacks?.onFrameDone?.(fid, result);
        return result;
      }
    };

    if (mode === "stagger") {
      const staggerResults: FrameRunResult[] = [];
      for (const fid of wave) {
        assertNotAborted(signal);
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
      const payload = await runFrameSliceParallel(wave, { refresh: true, signal });
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
  opts: { mode?: RunExecutionMode; dispatchAfter?: boolean; signal?: AbortSignal } = {},
  callbacks?: WaveCallbacks,
): Promise<OrchestratePayload & { squad_dispatch?: unknown }> {
  const signal = opts.signal;
  const payload = await executeSlicePlan(
    frameIds,
    opts.mode ?? "parallel",
    callbacks,
    { signal },
  );
  if (!opts.dispatchAfter) return payload;
  assertNotAborted(signal);
  const dispatch = await dispatchSquad(squadId, { signal });
  return { ...payload, squad_dispatch: dispatch };
}

/** Run multiple squads in parallel; per-squad progress via callbacks. */
export async function executeAllSquadsPlan(
  plans: { squadId: string; frameIds: string[] }[],
  mode: RunExecutionMode,
  opts: RunPlanOptions & { dispatchAfter?: boolean } = {},
  callbacks?: AllSquadsCallbacks,
): Promise<OrchestratePayload> {
  assertNotAborted(opts.signal);
  const payloads = await Promise.all(
    plans.map(async ({ squadId, frameIds }) => {
      callbacks?.onSquadStart?.(squadId, frameIds);
      const payload = await executeSquadSlicePlan(
        frameIds,
        squadId,
        { mode, dispatchAfter: opts.dispatchAfter, signal: opts.signal },
        {
          onFrameDone: (fid, result) => {
            callbacks?.onSquadFrameDone?.(squadId, fid, result);
          },
        },
      );
      callbacks?.onSquadDone?.(squadId, payload);
      return payload;
    }),
  );
  return mergeOrchestratePayloads(payloads);
}

/** Run squads one after another (lower API load than parallel). */
export async function executeAllSquadsPlanSequential(
  plans: { squadId: string; frameIds: string[] }[],
  mode: RunExecutionMode,
  opts: RunPlanOptions & { dispatchAfter?: boolean } = {},
  callbacks?: AllSquadsCallbacks,
): Promise<OrchestratePayload> {
  assertNotAborted(opts.signal);
  const payloads: OrchestratePayload[] = [];
  for (const { squadId, frameIds } of plans) {
    callbacks?.onSquadStart?.(squadId, frameIds);
    const payload = await executeSquadSlicePlan(
      frameIds,
      squadId,
      { mode, dispatchAfter: opts.dispatchAfter, signal: opts.signal },
      {
        onFrameDone: (fid, result) => {
          callbacks?.onSquadFrameDone?.(squadId, fid, result);
        },
      },
    );
    callbacks?.onSquadDone?.(squadId, payload);
    payloads.push(payload);
  }
  return mergeOrchestratePayloads(payloads);
}