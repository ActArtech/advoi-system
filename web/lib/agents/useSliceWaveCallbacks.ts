import { useCallback } from "react";
import type { Dispatch, SetStateAction } from "react";
import { runProgressModel } from "./agentSlices";
import type { WaveCallbacks } from "./runPlan";
import type { RunExecutionMode, SliceRunProgress } from "./types";

export type SliceWaveSetters = {
  setRunningFrames: Dispatch<SetStateAction<Set<string>>>;
  setQueuedFrames: Dispatch<SetStateAction<Set<string>>>;
  setProgress: Dispatch<SetStateAction<SliceRunProgress | null>>;
};

/** Build wave lifecycle callbacks for a single slice run. */
export function createSliceWaveCallbacks(
  waves: string[][],
  mode: RunExecutionMode,
  setters: SliceWaveSetters,
): WaveCallbacks {
  let currentWaveIndex = 0;
  let completedInWave = 0;
  const { setRunningFrames, setQueuedFrames, setProgress } = setters;

  return {
    onWaveStart: (wi, wave) => {
      currentWaveIndex = wi;
      completedInWave = 0;
      const upcoming = waves.slice(wi + 1).flat();
      setRunningFrames(new Set(wave));
      setQueuedFrames(new Set(upcoming));
      setProgress(runProgressModel(mode, wi, waves, 0));
    },
    onFrameDone: (fid) => {
      completedInWave += 1;
      setProgress(runProgressModel(mode, currentWaveIndex, waves, completedInWave));
      setRunningFrames((prev) => {
        const next = new Set(prev);
        next.delete(fid);
        return next;
      });
    },
    onWaveDone: (wi) => {
      completedInWave = 0;
      setProgress(runProgressModel(mode, wi + 1, waves, 0));
    },
  };
}

/** Returns a stable factory for slice wave callbacks (used by AgentsOrchestrator). */
export function useSliceWaveCallbacks(setters: SliceWaveSetters) {
  const { setRunningFrames, setQueuedFrames, setProgress } = setters;

  return useCallback(
    (waves: string[][], mode: RunExecutionMode) =>
      createSliceWaveCallbacks(waves, mode, {
        setRunningFrames,
        setQueuedFrames,
        setProgress,
      }),
    [setRunningFrames, setQueuedFrames, setProgress],
  );
}