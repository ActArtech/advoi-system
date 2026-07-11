"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Layers,
  Play,
  Rocket,
  RefreshCw,
  CheckSquare,
  Square,
  Zap,
  Waves,
  ListOrdered,
  Send,
  XCircle,
  History,
  ListPlus,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { AgentSliceTile } from "@/components/agents/AgentSliceTile";
import { SlicePresetsBar } from "@/components/agents/SlicePresetsBar";
import { SliceResultsDrawer } from "@/components/agents/SliceResultsDrawer";
import { SliceQueueDrawer } from "@/components/agents/SliceQueueDrawer";
import { SliceRunHistoryDrawer } from "@/components/agents/SliceRunHistoryDrawer";
import { SliceWavePreview } from "@/components/agents/SliceWavePreview";
import {
  buildAgentSlices,
  buildResultRows,
  buildSquadSlices,
  chunkFrameWaves,
  countFailedResults,
  countSlicesByPhase,
  frameIdsFromFailedResults,
  frameIdsForSquadSlice,
  resolveOrchestrateFrameIds,
  squadMembershipMap,
  squadRunProgressModel,
  squadWarmLabel,
} from "@/lib/agents/agentSlices";
import {
  deleteUserPreset,
  exportUserPresetsJson,
  importUserPresetsJson,
  readUserPresets,
  saveUserPreset,
  type UserSlicePreset,
} from "@/lib/agents/customUserPresets";
import { readPreferredRunMode, savePreferredRunMode } from "@/lib/agents/slicePreferences";
import { dispatchSquadsForAgent } from "@/lib/agents/sliceSquadDispatch";
import type { SlicePreset } from "@/lib/agents/slicePresets";
import {
  chainDraftLabel,
  deleteUserChain,
  exportUserChainsJson,
  importUserChainsJson,
  readUserChains,
  resolveUserChainPresets,
  saveUserChain,
  type UserPresetChain,
} from "@/lib/agents/customUserChains";
import {
  chainById,
  executePresetChain,
  executePresetsSequence,
  PRESET_CHAINS,
  resolveChainPresets,
} from "@/lib/agents/presetChain";
import { allPresetsForBar } from "@/lib/agents/slicePresets";
import {
  appendSliceRunLog,
  clearSliceRunLog,
  exportRunLogJson,
  importRunLogJson,
  readSliceRunLog,
} from "@/lib/agents/sliceRunLog";
import {
  executeAllSquadsPlan,
  executeAllSquadsPlanSequential,
  executeSlicePlan,
  executeSquadSlicePlan,
} from "@/lib/agents/runPlan";
import { useSliceWaveCallbacks } from "@/lib/agents/useSliceWaveCallbacks";
import {
  dispatchAllSquads,
  fetchAgents,
  fetchFrames,
  fetchSquads,
  runSixParallel,
} from "@/lib/agents/orchestrateClient";
import { useTabNavigation } from "@/components/shell/TabContext";
import type {
  AgentSliceModel,
  FrameRunResult,
  OrchestratePayload,
  RunExecutionMode,
  SliceRunLogEntry,
  SliceRunProgress,
  SquadSliceModel,
} from "@/lib/agents/types";
import { RUN_FRAME_EVENT } from "@/components/pwaOnboarding";
import { useJsonFilePicker } from "@/hooks/useJsonFilePicker";
import { useSliceKeyboard } from "@/hooks/useSliceKeyboard";
import {
  bumpQueueItem,
  createQueueEntry,
  dequeueSliceRun,
  enqueueSliceRun,
  moveQueueItem,
  queueItemSnapshots,
  removeQueueItem,
  type SliceQueueEntry,
  type SliceQueueItem,
} from "@/lib/agents/sliceRunQueue";
import {
  detectVoiceMirrorComplete,
  isFailedMirrorStatus,
  shouldMirrorVoiceFrame,
  voiceMirrorLogLabel,
  voiceMirrorLogMode,
  voiceMirrorResultFromAgent,
  voiceMirrorStatusLabel,
  type RunFrameDetail,
} from "@/lib/agents/voiceFrameBridge";
import { cn } from "@/lib/utils";

function downloadJsonFile(filename: string, json: string) {
  const blob = new Blob([json], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

const MODE_OPTIONS: { mode: RunExecutionMode; label: string; icon: typeof Zap }[] = [
  { mode: "parallel", label: "Parallel", icon: Zap },
  { mode: "wave", label: "Wave x2", icon: Waves },
  { mode: "stagger", label: "Stagger", icon: ListOrdered },
];

export function AgentsOrchestrator() {
  const tabNav = useTabNavigation();
  const [agents, setAgents] = useState<Awaited<ReturnType<typeof fetchAgents>>>([]);
  const [frames, setFrames] = useState<Awaited<ReturnType<typeof fetchFrames>>>([]);
  const [squads, setSquads] = useState<Awaited<ReturnType<typeof fetchSquads>>>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [multiMode, setMultiMode] = useState(false);
  const [runMode, setRunMode] = useState<RunExecutionMode>("parallel");
  const [busy, setBusy] = useState(false);
  const [runningFrames, setRunningFrames] = useState<Set<string>>(new Set());
  const [queuedFrames, setQueuedFrames] = useState<Set<string>>(new Set());
  const [lastResults, setLastResults] = useState<FrameRunResult[]>([]);
  const [status, setStatus] = useState("Load agents to run parallel slices.");
  const [lastPayload, setLastPayload] = useState<OrchestratePayload | null>(null);
  const [progress, setProgress] = useState<SliceRunProgress | null>(null);
  const [resultsOpen, setResultsOpen] = useState(false);
  const [activeSquadId, setActiveSquadId] = useState<string | null>(null);
  const [squadProgress, setSquadProgress] = useState<{ done: number; total: number } | null>(
    null,
  );
  const [squadFrameProgress, setSquadFrameProgress] = useState<ReturnType<
    typeof squadRunProgressModel
  > | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [historyLog, setHistoryLog] = useState<SliceRunLogEntry[]>([]);
  const [userPresets, setUserPresets] = useState<UserSlicePreset[]>([]);
  const [focusFrameId, setFocusFrameId] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const runQueueRef = useRef<SliceQueueEntry[]>([]);
  const voiceMirrorPollRef = useRef<number | null>(null);
  const voiceMirrorFrameRef = useRef<string | null>(null);
  const voiceMirrorStartRef = useRef<number>(0);
  const voiceMirrorSourceRef = useRef<string | undefined>(undefined);
  const runLogMetaRef = useRef<{ label: string; mode: RunExecutionMode }>({
    label: "Run",
    mode: "parallel",
  });
  const squadFramesDoneRef = useRef(0);
  const squadSquadsDoneRef = useRef(0);
  const [queueDepth, setQueueDepth] = useState(0);
  const [queueSnapshot, setQueueSnapshot] = useState<SliceQueueItem[]>([]);
  const [queueOpen, setQueueOpen] = useState(false);
  const [userChains, setUserChains] = useState<UserPresetChain[]>([]);
  const [chainBuilderMode, setChainBuilderMode] = useState(false);
  const [chainDraftIds, setChainDraftIds] = useState<string[]>([]);
  const [chainDispatchDraft, setChainDispatchDraft] = useState(false);

  const createWaveCallbacks = useSliceWaveCallbacks({
    setRunningFrames,
    setQueuedFrames,
    setProgress,
  });

  const clearVoiceMirrorPoll = useCallback(() => {
    if (voiceMirrorPollRef.current != null) {
      window.clearInterval(voiceMirrorPollRef.current);
      voiceMirrorPollRef.current = null;
    }
  }, []);

  const completeVoiceMirror = useCallback(
    (agentList: Awaited<ReturnType<typeof fetchAgents>>) => {
      const frameId = voiceMirrorFrameRef.current;
      if (!frameId) return false;
      if (!detectVoiceMirrorComplete(frameId, agentList, voiceMirrorStartRef.current)) {
        return false;
      }
      clearVoiceMirrorPoll();
      voiceMirrorFrameRef.current = null;
      setRunningFrames(new Set());
      const mirrored = voiceMirrorResultFromAgent(frameId, agentList);
      const source = voiceMirrorSourceRef.current;
      voiceMirrorSourceRef.current = undefined;
      if (mirrored) {
        setLastResults([mirrored]);
        const summary = mirrored.spoken_summary || `${mirrored.status ?? "ok"} · ${frameId}`;
        setStatus(`Voice sync complete: ${summary}`);
        const failed = isFailedMirrorStatus(mirrored.status);
        setHistoryLog(
          appendSliceRunLog({
            label: voiceMirrorLogLabel(frameId, source),
            mode: voiceMirrorLogMode(frameId),
            frameCount: 1,
            okCount: failed ? 0 : 1,
            failCount: failed ? 1 : 0,
            summary: mirrored.spoken_summary,
            frameIds: [frameId],
          }),
        );
        setResultsOpen(true);
      } else {
        setStatus(`Voice sync complete: ${frameId}`);
      }
      return true;
    },
    [clearVoiceMirrorPoll],
  );

  const reload = useCallback(async () => {
    try {
      const [a, f, s] = await Promise.all([fetchAgents(), fetchFrames(), fetchSquads()]);
      setAgents(a);
      setFrames(f);
      setSquads(s);
      const mirrored = completeVoiceMirror(a);
      if (!mirrored && !busy && !voiceMirrorFrameRef.current) {
        const warm = a.filter((x) => x.cached).length;
        setStatus(`Ready · ${warm}/${a.length || 6} warm · ${s.length} squads`);
      }
    } catch {
      if (!busy && !voiceMirrorFrameRef.current) {
        setStatus("Could not load agents. Is the API up?");
      }
    }
  }, [busy, completeVoiceMirror]);

  useEffect(() => {
    const savedMode = readPreferredRunMode();
    if (savedMode) setRunMode(savedMode);
    setHistoryLog(readSliceRunLog());
    setUserPresets(readUserPresets());
    setUserChains(readUserChains());
    void reload();
    const t = window.setInterval(() => void reload(), 20_000);
    return () => window.clearInterval(t);
  }, [reload]);

  const squadMap = useMemo(() => squadMembershipMap(squads), [squads]);

  const agentSlices = useMemo(
    () =>
      buildAgentSlices(agents, frames, {
        selectedIds: selected,
        runningFrameIds: runningFrames,
        queuedFrameIds: queuedFrames,
        results: lastResults,
        squadByAgent: squadMap,
      }),
    [agents, frames, selected, runningFrames, queuedFrames, lastResults, squadMap],
  );

  const squadSlices = useMemo(() => buildSquadSlices(squads, agents), [squads, agents]);
  const phaseCounts = useMemo(() => countSlicesByPhase(agentSlices), [agentSlices]);
  const resultRows = useMemo(
    () => buildResultRows(agentSlices, lastResults),
    [agentSlices, lastResults],
  );
  const failedCount = useMemo(() => countFailedResults(lastResults), [lastResults]);
  const previewFrameIds = useMemo(
    () =>
      resolveOrchestrateFrameIds(
        agentSlices,
        selected.size > 0 ? "selected" : "all_six",
      ),
    [agentSlices, selected.size],
  );

  const toggleSelect = (agentId: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(agentId)) next.delete(agentId);
      else next.add(agentId);
      return next;
    });
  };

  const beginRun = () => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    return controller;
  };

  const resetRunUi = () => {
    setRunningFrames(new Set());
    setQueuedFrames(new Set());
    setProgress(null);
    setActiveSquadId(null);
    setSquadProgress(null);
    setSquadFrameProgress(null);
    squadFramesDoneRef.current = 0;
    squadSquadsDoneRef.current = 0;
  };

  const syncQueueUi = useCallback(() => {
    setQueueSnapshot(queueItemSnapshots(runQueueRef.current));
    setQueueDepth(runQueueRef.current.length);
  }, []);

  const processRunQueue = useCallback(() => {
    if (busy) return;
    const { queue, next } = dequeueSliceRun(runQueueRef.current);
    runQueueRef.current = queue;
    syncQueueUi();
    if (!next) return;
    const waiting = queue.length;
    setStatus(
      waiting > 0 ? `Dequeuing: ${next.label} · ${waiting} queued` : `Dequeuing: ${next.label}`,
    );
    void next.run();
  }, [busy, syncQueueUi]);

  const scheduleRun = useCallback(
    (label: string, runFn: () => Promise<void>) => {
      if (busy) {
        runQueueRef.current = enqueueSliceRun(
          runQueueRef.current,
          createQueueEntry(label, runFn),
        );
        syncQueueUi();
        setStatus(`Queued "${label}" · ${runQueueRef.current.length} waiting`);
        return;
      }
      void runFn();
    },
    [busy, syncQueueUi],
  );

  const clearRunQueue = useCallback(() => {
    runQueueRef.current = [];
    syncQueueUi();
    setStatus("Run queue cleared.");
  }, [syncQueueUi]);

  const removeFromQueue = useCallback(
    (id: string) => {
      runQueueRef.current = removeQueueItem(runQueueRef.current, id);
      syncQueueUi();
      setStatus("Removed from queue.");
    },
    [syncQueueUi],
  );

  const bumpInQueue = useCallback(
    (id: string) => {
      runQueueRef.current = bumpQueueItem(runQueueRef.current, id);
      syncQueueUi();
      setStatus("Moved to front of queue.");
    },
    [syncQueueUi],
  );

  const moveInQueue = useCallback(
    (id: string, direction: "up" | "down") => {
      runQueueRef.current = moveQueueItem(runQueueRef.current, id, direction);
      syncQueueUi();
      setStatus(direction === "up" ? "Moved batch up." : "Moved batch down.");
    },
    [syncQueueUi],
  );

  useEffect(() => {
    if (!busy) processRunQueue();
  }, [busy, processRunQueue]);

  useEffect(() => {
    return () => clearVoiceMirrorPoll();
  }, [clearVoiceMirrorPoll]);

  useEffect(() => {
    const onFrame = (ev: Event) => {
      const detail = (ev as CustomEvent<RunFrameDetail>).detail;
      if (detail?.frameId) {
        tabNav?.scrollToTab("agents");
        setFocusFrameId(detail.frameId);
        window.setTimeout(() => setFocusFrameId(null), 3000);
      }
      if (shouldMirrorVoiceFrame(detail)) {
        clearVoiceMirrorPoll();
        voiceMirrorStartRef.current = Date.now();
        voiceMirrorFrameRef.current = detail.frameId ?? null;
        voiceMirrorSourceRef.current = detail.source;
        setRunningFrames(new Set(detail?.frameId ? [detail.frameId] : []));
        setStatus(voiceMirrorStatusLabel(detail!));
        void reload();
        voiceMirrorPollRef.current = window.setInterval(() => void reload(), 2000);
        const frameId = detail.frameId;
        window.setTimeout(() => {
          if (voiceMirrorFrameRef.current !== frameId) return;
          clearVoiceMirrorPoll();
          voiceMirrorFrameRef.current = null;
          setRunningFrames(new Set());
          void reload();
          setStatus(`Voice sync timed out: ${frameId ?? "slice"}`);
        }, 30_000);
        return;
      }
      void reload();
    };
    window.addEventListener(RUN_FRAME_EVENT, onFrame);
    return () => window.removeEventListener(RUN_FRAME_EVENT, onFrame);
  }, [reload, tabNav, clearVoiceMirrorPoll]);

  const isAbortError = (err: unknown) =>
    err instanceof DOMException && err.name === "AbortError";

  const cancelRun = () => {
    abortRef.current?.abort();
    clearVoiceMirrorPoll();
    setBusy(false);
    resetRunUi();
    setStatus("Run cancelled.");
  };

  const finishRun = (data: OrchestratePayload, frameIds: string[]) => {
    setLastPayload(data);
    const results = data.results ?? [];
    setLastResults(results);
    const failCount = countFailedResults(results);
    setHistoryLog(
      appendSliceRunLog({
        label: runLogMetaRef.current.label,
        mode: runLogMetaRef.current.mode,
        frameCount: frameIds.length,
        okCount: results.length - failCount,
        failCount,
        summary: data.spoken_summary,
        frameIds: frameIds.length > 0 ? frameIds : undefined,
      }),
    );
    resetRunUi();
    const squadNote =
      data.squads?.dispatched != null
        ? ` · Squads ${data.squads.dispatched}/${data.squads.total}`
        : "";
    setStatus((data.spoken_summary || `Completed ${frameIds.length} slices.`) + squadNote);
    if (results.length > 1) setResultsOpen(true);
    void reload();
  };

  const runWithPlanInternal = useCallback(
    async (frameIds: string[], mode: RunExecutionMode, label: string) => {
      if (frameIds.length === 0) return;
      const waves = chunkFrameWaves(frameIds, mode);
      const controller = beginRun();
      runLogMetaRef.current = { label, mode };
      setBusy(true);
      setLastResults([]);
      setStatus(`${label} (${mode}, ${frameIds.length} slices)...`);

      try {
        const payload = await executeSlicePlan(
          frameIds,
          mode,
          createWaveCallbacks(waves, mode),
          { signal: controller.signal },
        );
        finishRun(payload, frameIds);
      } catch (err) {
        resetRunUi();
        setStatus(isAbortError(err) ? "Run cancelled." : err instanceof Error ? err.message : "Run failed");
      } finally {
        setBusy(false);
      }
    },
    [createWaveCallbacks],
  );

  const runWithPlan = useCallback(
    (frameIds: string[], mode: RunExecutionMode, label: string) => {
      if (frameIds.length === 0) return;
      scheduleRun(label, () => runWithPlanInternal(frameIds, mode, label));
    },
    [scheduleRun, runWithPlanInternal],
  );

  const runParallelInternal = useCallback(
    async (scope: "selected" | "all_six" | "six_squads") => {
      if (scope === "six_squads") {
        const frameIds = [...resolveOrchestrateFrameIds(agentSlices, "all_six")];
        const controller = beginRun();
        runLogMetaRef.current = { label: "6 + squads", mode: runMode };
        setBusy(true);
        setRunningFrames(new Set(frameIds));
        setStatus("Running all 6 + dispatching squads...");
        try {
          const data = await runSixParallel({
            dispatchSquads: true,
            refresh: true,
            signal: controller.signal,
          });
          finishRun(data, frameIds);
        } catch (err) {
          resetRunUi();
          setStatus(
            isAbortError(err) ? "Run cancelled." : err instanceof Error ? err.message : "Run-six failed",
          );
        } finally {
          setBusy(false);
        }
        return;
      }
      const frameIds = resolveOrchestrateFrameIds(
        agentSlices,
        scope === "selected" ? "selected" : "all_six",
      );
      await runWithPlanInternal(
        frameIds,
        runMode,
        scope === "selected" ? "Selected run" : "All six",
      );
    },
    [agentSlices, runMode, runWithPlanInternal],
  );

  const runParallel = useCallback(
    (scope: "selected" | "all_six" | "six_squads") => {
      const label =
        scope === "selected" ? "Selected run" : scope === "six_squads" ? "6 + squads" : "All six";
      scheduleRun(label, () => runParallelInternal(scope));
    },
    [scheduleRun, runParallelInternal],
  );

  const runSquadSliceInternal = useCallback(
    async (squad: SquadSliceModel, dispatchAfter: boolean) => {
      const frameIds = frameIdsForSquadSlice(squad, frames);
      if (frameIds.length === 0) {
        setStatus(`No frames mapped for ${squad.name}`);
        return;
      }
      setActiveSquadId(squad.squadId);
      const waves = chunkFrameWaves(frameIds, runMode);
      const controller = beginRun();
      runLogMetaRef.current = {
        label: dispatchAfter ? `Squad ${squad.name} + dispatch` : `Squad ${squad.name}`,
        mode: runMode,
      };
      setBusy(true);
      setLastResults([]);
      setStatus(
        dispatchAfter
          ? `Squad ${squad.name}: run + dispatch...`
          : `Squad ${squad.name}: ${frameIds.length} slices (${runMode})...`,
      );

      try {
        const payload = await executeSquadSlicePlan(
          frameIds,
          squad.squadId,
          { mode: runMode, dispatchAfter, signal: controller.signal },
          createWaveCallbacks(waves, runMode),
        );
        finishRun(payload, frameIds);
      } catch (err) {
        resetRunUi();
        setStatus(
          isAbortError(err) ? "Run cancelled." : err instanceof Error ? err.message : "Squad run failed",
        );
      } finally {
        setBusy(false);
      }
    },
    [frames, runMode, createWaveCallbacks],
  );

  const runSquadSlice = useCallback(
    (squad: SquadSliceModel, dispatchAfter: boolean) => {
      const label = dispatchAfter ? `Squad ${squad.name} + dispatch` : `Squad ${squad.name}`;
      scheduleRun(label, () => runSquadSliceInternal(squad, dispatchAfter));
    },
    [scheduleRun, runSquadSliceInternal],
  );

  const runAllSquadsInternal = useCallback(
    async (dispatchAfter: boolean) => {
      if (squads.length <= 1) return;

      const plans = squadSlices
        .map((squad) => ({
          squad,
          frameIds: frameIdsForSquadSlice(squad, frames),
        }))
        .filter((p) => p.frameIds.length > 0);

      if (plans.length === 0) {
        setStatus("No frames mapped for squads");
        return;
      }

      const allFrameIds = plans.flatMap((p) => p.frameIds);
      const controller = beginRun();
      runLogMetaRef.current = {
        label: dispatchAfter ? "All squads + dispatch" : "All squads",
        mode: runMode,
      };
      squadFramesDoneRef.current = 0;
      squadSquadsDoneRef.current = 0;
      setBusy(true);
      setLastResults([]);
      setRunningFrames(new Set(allFrameIds));
      setQueuedFrames(new Set());
      setProgress(null);
      setSquadProgress({ done: 0, total: plans.length });
      setSquadFrameProgress(squadRunProgressModel(0, plans.length, 0, allFrameIds.length));
      setStatus(
        dispatchAfter
          ? `Running ${plans.length} squads + dispatch (${allFrameIds.length} slices)...`
          : `Running ${plans.length} squads in parallel (${allFrameIds.length} slices)...`,
      );

      const updateSquadFrameProgress = () => {
        setSquadFrameProgress(
          squadRunProgressModel(
            squadSquadsDoneRef.current,
            plans.length,
            squadFramesDoneRef.current,
            allFrameIds.length,
          ),
        );
      };

      try {
        const payload = await executeAllSquadsPlan(
          plans.map(({ squad, frameIds }) => ({ squadId: squad.squadId, frameIds })),
          runMode,
          { signal: controller.signal, dispatchAfter },
          {
            onSquadStart: (squadId) => setActiveSquadId(squadId),
            onSquadFrameDone: () => {
              squadFramesDoneRef.current += 1;
              updateSquadFrameProgress();
            },
            onSquadDone: () => {
              squadSquadsDoneRef.current += 1;
              setSquadProgress((prev) =>
                prev ? { ...prev, done: Math.min(prev.done + 1, prev.total) } : null,
              );
              updateSquadFrameProgress();
            },
          },
        );
        finishRun(payload, allFrameIds);
      } catch (err) {
        resetRunUi();
        setStatus(
          isAbortError(err)
            ? "Run cancelled."
            : err instanceof Error
              ? err.message
              : dispatchAfter
                ? "Run all squads + dispatch failed"
                : "Run all squads failed",
        );
      } finally {
        setBusy(false);
      }
    },
    [squads.length, squadSlices, frames, runMode],
  );

  const runAllSquads = useCallback(
    () => scheduleRun("All squads", () => runAllSquadsInternal(false)),
    [scheduleRun, runAllSquadsInternal],
  );

  const runAllSquadsDispatch = useCallback(
    () => scheduleRun("All squads + dispatch", () => runAllSquadsInternal(true)),
    [scheduleRun, runAllSquadsInternal],
  );

  const runPreset = useCallback(
    (preset: SlicePreset) => {
      setRunMode(preset.mode);
      runWithPlan([...preset.frameIds], preset.mode, preset.label);
    },
    [runWithPlan],
  );

  const runPresetChainInternal = useCallback(
    async (chainId: string) => {
      const chain = chainById(chainId);
      if (!chain) return;
      const presets = resolveChainPresets(chain);
      if (presets.length === 0) return;
      const controller = beginRun();
      runLogMetaRef.current = { label: chain.label, mode: presets[0].mode };
      setBusy(true);
      setLastResults([]);
      setStatus(`${chain.label}: ${presets.length} stages...`);
      try {
        const payload = await executePresetChain(
          chain,
          async (preset) => {
            const frameIds = [...preset.frameIds];
            const waves = chunkFrameWaves(frameIds, preset.mode);
            setRunMode(preset.mode);
            setStatus(`${chain.label}: ${preset.label}...`);
            return executeSlicePlan(
              frameIds,
              preset.mode,
              createWaveCallbacks(waves, preset.mode),
              { signal: controller.signal },
            );
          },
          chain.dispatchAfter
            ? () => {
                setStatus(`${chain.label}: dispatching squads...`);
                return dispatchAllSquads({ signal: controller.signal });
              }
            : undefined,
        );
        const allFrameIds = presets.flatMap((p) => [...p.frameIds]);
        finishRun(payload, allFrameIds);
      } catch (err) {
        resetRunUi();
        setStatus(
          isAbortError(err) ? "Run cancelled." : err instanceof Error ? err.message : "Chain failed",
        );
      } finally {
        setBusy(false);
      }
    },
    [createWaveCallbacks],
  );

  const runPresetChain = useCallback(
    (chainId: string) => {
      const chain = chainById(chainId);
      if (!chain) return;
      scheduleRun(chain.label, () => runPresetChainInternal(chainId));
    },
    [scheduleRun, runPresetChainInternal],
  );

  const runUserChainInternal = useCallback(
    async (chain: UserPresetChain) => {
      const presets = resolveUserChainPresets(chain, userPresets);
      if (presets.length === 0) return;
      const controller = beginRun();
      runLogMetaRef.current = { label: chain.label, mode: presets[0].mode };
      setBusy(true);
      setLastResults([]);
      setStatus(`${chain.label}: ${presets.length} stages...`);
      try {
        const payload = await executePresetsSequence(
          presets,
          async (preset) => {
            const frameIds = [...preset.frameIds];
            const waves = chunkFrameWaves(frameIds, preset.mode);
            setRunMode(preset.mode);
            setStatus(`${chain.label}: ${preset.label}...`);
            return executeSlicePlan(
              frameIds,
              preset.mode,
              createWaveCallbacks(waves, preset.mode),
              { signal: controller.signal },
            );
          },
          chain.dispatchAfter
            ? () => {
                setStatus(`${chain.label}: dispatching squads...`);
                return dispatchAllSquads({ signal: controller.signal });
              }
            : undefined,
        );
        const allFrameIds = presets.flatMap((p) => [...p.frameIds]);
        finishRun(payload, allFrameIds);
      } catch (err) {
        resetRunUi();
        setStatus(
          isAbortError(err) ? "Run cancelled." : err instanceof Error ? err.message : "Chain failed",
        );
      } finally {
        setBusy(false);
      }
    },
    [userPresets, createWaveCallbacks],
  );

  const runUserChain = useCallback(
    (chain: UserPresetChain) => {
      scheduleRun(chain.label, () => runUserChainInternal(chain));
    },
    [scheduleRun, runUserChainInternal],
  );

  const dispatchAllSquadsInternal = useCallback(async () => {
    if (squads.length === 0) return;
    const controller = beginRun();
    runLogMetaRef.current = { label: "Dispatch all squads", mode: runMode };
    setBusy(true);
    setStatus("Dispatching all squads...");
    try {
      const data = await dispatchAllSquads({ signal: controller.signal });
      finishRun(data, []);
      setStatus(
        `Dispatched ${data.squads?.dispatched ?? 0}/${data.squads?.total ?? squads.length} squads`,
      );
    } catch (err) {
      resetRunUi();
      setStatus(
        isAbortError(err) ? "Run cancelled." : err instanceof Error ? err.message : "Dispatch-all failed",
      );
    } finally {
      setBusy(false);
    }
  }, [squads.length, runMode]);

  const dispatchAllSquadsOnly = useCallback(
    () => scheduleRun("Dispatch all squads", () => dispatchAllSquadsInternal()),
    [scheduleRun, dispatchAllSquadsInternal],
  );

  const saveCustomPreset = useCallback(() => {
    const picked = agentSlices.filter((s) => selected.has(s.agentId));
    if (picked.length === 0) return;
    const label = picked.map((s) => s.shortLabel).join(" + ");
    const frameIds = picked.map((s) => s.frameId);
    setUserPresets(saveUserPreset({ label, frameIds, mode: runMode }));
    setStatus(`Saved preset "${label}"`);
  }, [agentSlices, selected, runMode]);

  const removeUserPreset = useCallback((id: string) => {
    setUserPresets(deleteUserPreset(id));
    setStatus("Preset removed");
  }, []);

  const allPresets = useMemo(
    () => allPresetsForBar(userPresets),
    [userPresets],
  );

  const toggleChainPreset = useCallback((presetId: string) => {
    setChainDraftIds((prev) =>
      prev.includes(presetId) ? prev.filter((id) => id !== presetId) : [...prev, presetId],
    );
  }, []);

  const saveCustomChain = useCallback(() => {
    if (chainDraftIds.length < 2) return;
    let label = chainDraftLabel(chainDraftIds, allPresets);
    if (chainDispatchDraft) label += " → Dispatch";
    setUserChains(
      saveUserChain({
        label,
        presetIds: chainDraftIds,
        dispatchAfter: chainDispatchDraft || undefined,
      }),
    );
    setChainDraftIds([]);
    setChainDispatchDraft(false);
    setChainBuilderMode(false);
    setStatus(`Saved chain "${label}"`);
  }, [chainDraftIds, chainDispatchDraft, allPresets]);

  const removeUserChain = useCallback((id: string) => {
    setUserChains(deleteUserChain(id));
    setStatus("Chain removed");
  }, []);

  const rerunFromHistory = useCallback(
    (entry: SliceRunLogEntry) => {
      if (!entry.frameIds?.length) return;
      setHistoryOpen(false);
      setRunMode(entry.mode);
      runWithPlan([...entry.frameIds], entry.mode, `Re-run: ${entry.label}`);
    },
    [runWithPlan],
  );

  const runAllSquadsSequentialInternal = useCallback(
    async (dispatchAfter: boolean) => {
      if (squads.length <= 1) return;

      const plans = squadSlices
        .map((squad) => ({
          squad,
          frameIds: frameIdsForSquadSlice(squad, frames),
        }))
        .filter((p) => p.frameIds.length > 0);

      if (plans.length === 0) {
        setStatus("No frames mapped for squads");
        return;
      }

      const allFrameIds = plans.flatMap((p) => p.frameIds);
      const controller = beginRun();
      runLogMetaRef.current = {
        label: dispatchAfter ? "All squads sequential + dispatch" : "All squads sequential",
        mode: runMode,
      };
      squadFramesDoneRef.current = 0;
      squadSquadsDoneRef.current = 0;
      setBusy(true);
      setLastResults([]);
      setRunningFrames(new Set(allFrameIds));
      setQueuedFrames(new Set());
      setProgress(null);
      setSquadProgress({ done: 0, total: plans.length });
      setSquadFrameProgress(squadRunProgressModel(0, plans.length, 0, allFrameIds.length));
      setStatus(
        dispatchAfter
          ? `Sequential squads + dispatch (${plans.length} crews)...`
          : `Sequential squads (${plans.length} crews)...`,
      );

      const updateSquadFrameProgress = () => {
        setSquadFrameProgress(
          squadRunProgressModel(
            squadSquadsDoneRef.current,
            plans.length,
            squadFramesDoneRef.current,
            allFrameIds.length,
          ),
        );
      };

      try {
        const payload = await executeAllSquadsPlanSequential(
          plans.map(({ squad, frameIds }) => ({ squadId: squad.squadId, frameIds })),
          runMode,
          { signal: controller.signal, dispatchAfter },
          {
            onSquadStart: (squadId) => setActiveSquadId(squadId),
            onSquadFrameDone: () => {
              squadFramesDoneRef.current += 1;
              updateSquadFrameProgress();
            },
            onSquadDone: () => {
              squadSquadsDoneRef.current += 1;
              setSquadProgress((prev) =>
                prev ? { ...prev, done: Math.min(prev.done + 1, prev.total) } : null,
              );
              updateSquadFrameProgress();
            },
          },
        );
        finishRun(payload, allFrameIds);
      } catch (err) {
        resetRunUi();
        setStatus(
          isAbortError(err) ? "Run cancelled." : err instanceof Error ? err.message : "Sequential squads failed",
        );
      } finally {
        setBusy(false);
      }
    },
    [squads.length, squadSlices, frames, runMode],
  );

  const runAllSquadsSequential = useCallback(
    (dispatchAfter: boolean) => {
      const label = dispatchAfter ? "All squads sequential + dispatch" : "All squads sequential";
      scheduleRun(label, () => runAllSquadsSequentialInternal(dispatchAfter));
    },
    [scheduleRun, runAllSquadsSequentialInternal],
  );

  const retryFailed = useCallback(() => {
    const frameIds = frameIdsFromFailedResults(lastResults);
    if (frameIds.length === 0) return;
    runWithPlan(frameIds, runMode, "Retry failed");
  }, [lastResults, runMode, runWithPlan]);

  const runOneSlice = useCallback(
    (slice: AgentSliceModel) => {
      runWithPlan([slice.frameId], "stagger", slice.shortLabel);
    },
    [runWithPlan],
  );

  const onSliceTap = (slice: AgentSliceModel) => {
    if (multiMode) {
      toggleSelect(slice.agentId);
      return;
    }
    void runOneSlice(slice);
  };

  const dispatchSliceSquadsInternal = useCallback(
    async (slice: AgentSliceModel) => {
      if (slice.squadIds.length === 0) return;
      const controller = beginRun();
      runLogMetaRef.current = {
        label: `Dispatch ${slice.shortLabel} squads`,
        mode: runMode,
      };
      setBusy(true);
      setStatus(`Long-press: dispatching squads for ${slice.shortLabel}...`);
      try {
        const data = await dispatchSquadsForAgent(slice.agentId, squads, {
          signal: controller.signal,
        });
        finishRun(data, []);
        setStatus(
          `Dispatched ${data.squads?.dispatched ?? 0} squad(s) for ${slice.shortLabel}`,
        );
      } catch (err) {
        resetRunUi();
        setStatus(
          isAbortError(err)
            ? "Run cancelled."
            : err instanceof Error
              ? err.message
              : "Squad dispatch failed",
        );
      } finally {
        setBusy(false);
      }
    },
    [squads, runMode],
  );

  const dispatchSliceSquads = useCallback(
    (slice: AgentSliceModel) => {
      scheduleRun(`Dispatch ${slice.shortLabel} squads`, () => dispatchSliceSquadsInternal(slice));
    },
    [scheduleRun, dispatchSliceSquadsInternal],
  );

  const presetsFilePicker = useJsonFilePicker({
    onJson: (raw) => {
      try {
        setUserPresets(importUserPresetsJson(raw));
        setStatus("Presets imported");
      } catch {
        setStatus("Invalid presets JSON");
      }
    },
    onError: (msg) => setStatus(msg),
  });

  const chainsFilePicker = useJsonFilePicker({
    onJson: (raw) => {
      try {
        const imported = importUserChainsJson(raw);
        setUserChains(imported);
        setStatus(`Imported ${imported.length} chain(s)`);
      } catch {
        setStatus("Invalid chains JSON");
      }
    },
    onError: (msg) => setStatus(msg),
  });

  const historyFilePicker = useJsonFilePicker({
    onJson: (raw) => {
      try {
        const entries = importRunLogJson(raw);
        setHistoryLog(entries);
        setStatus(`Imported ${entries.length} history entries`);
      } catch {
        setStatus("Invalid history JSON");
      }
    },
    onError: (msg) => setStatus(msg),
  });

  useSliceKeyboard({
    slices: agentSlices,
    busy,
    failedCount,
    onRunSlice: runOneSlice,
    onRetryFailed: retryFailed,
    onCancel: cancelRun,
    onToggleMulti: () => setMultiMode((m) => !m),
  });

  const exportHistory = useCallback(() => {
    downloadJsonFile("advoi-slice-history.json", exportRunLogJson(historyLog));
    setStatus("History exported");
  }, [historyLog]);

  const importHistory = useCallback(() => {
    historyFilePicker.openPicker();
  }, [historyFilePicker]);

  const exportPresets = useCallback(() => {
    downloadJsonFile("advoi-slice-presets.json", exportUserPresetsJson(userPresets));
    setStatus("Presets exported");
  }, [userPresets]);

  const importPresets = useCallback(() => {
    presetsFilePicker.openPicker();
  }, [presetsFilePicker]);

  const exportChains = useCallback(() => {
    downloadJsonFile("advoi-slice-chains.json", exportUserChainsJson(userChains));
    setStatus("Chains exported");
  }, [userChains]);

  const importChains = useCallback(() => {
    chainsFilePicker.openPicker();
  }, [chainsFilePicker]);

  const warmCount = agents.filter((a) => a.cached).length;
  const totalAgents = agents.length || 6;

  return (
    <div className="space-y-4" data-testid="agents-orchestrator">
      <input
        ref={presetsFilePicker.inputRef}
        type="file"
        accept="application/json,.json"
        className="sr-only"
        aria-hidden
        tabIndex={-1}
        onChange={presetsFilePicker.onChange}
        data-testid="import-presets-file-input"
      />
      <input
        ref={historyFilePicker.inputRef}
        type="file"
        accept="application/json,.json"
        className="sr-only"
        aria-hidden
        tabIndex={-1}
        onChange={historyFilePicker.onChange}
        data-testid="import-history-file-input"
      />
      <input
        ref={chainsFilePicker.inputRef}
        type="file"
        accept="application/json,.json"
        className="sr-only"
        aria-hidden
        tabIndex={-1}
        onChange={chainsFilePicker.onChange}
        data-testid="import-chains-file-input"
      />
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant={warmCount === totalAgents ? "success" : "secondary"}>
          {warmCount}/{totalAgents} warm
        </Badge>
        {lastPayload?.squads?.dispatched != null ? (
          <Badge variant="default">
            Squads {lastPayload.squads.dispatched}/{lastPayload.squads.total}
          </Badge>
        ) : null}
        {phaseCounts.running > 0 ? (
          <Badge variant="warning" data-testid="active-slice-count">
            {phaseCounts.running} running
          </Badge>
        ) : null}
        {busy && runningFrames.size > 0 ? (
          <Badge variant="outline" data-testid="concurrent-frame-count">
            {runningFrames.size} active
          </Badge>
        ) : null}
        {phaseCounts.queued > 0 ? (
          <Badge variant="outline">{phaseCounts.queued} queued</Badge>
        ) : null}
        {squadProgress && busy ? (
          <Badge variant="default" data-testid="squad-run-progress">
            Squads {squadProgress.done}/{squadProgress.total}
          </Badge>
        ) : null}
        {queueDepth > 0 ? (
          <button
            type="button"
            className="inline-flex"
            onClick={() => setQueueOpen(true)}
            data-testid="slice-run-queue-depth"
          >
            <Badge variant="outline" className="cursor-pointer hover:bg-secondary/80">
              {queueDepth} queued
            </Badge>
          </button>
        ) : null}
      </div>

      <div className="flex flex-wrap gap-1.5" role="group" aria-label="Run mode">
        {MODE_OPTIONS.map(({ mode, label, icon: Icon }) => (
          <Button
            key={mode}
            size="sm"
            variant={runMode === mode ? "default" : "outline"}
            disabled={busy}
            onClick={() => {
              setRunMode(mode);
              savePreferredRunMode(mode);
            }}
            data-testid={`run-mode-${mode}`}
          >
            <Icon className="h-3.5 w-3.5" />
            {label}
          </Button>
        ))}
      </div>

      {progress && busy ? (
        <div className="space-y-1" data-testid="slice-run-progress">
          <div className="flex justify-between text-[10px] text-muted-foreground">
            <span>
              Wave {Math.min(progress.waveIndex + 1, progress.waveCount)}/{progress.waveCount}
            </span>
            <span>{progress.percent}%</span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-secondary">
            <div
              className="h-full rounded-full bg-primary transition-all duration-300"
              style={{ width: `${progress.percent}%` }}
            />
          </div>
        </div>
      ) : null}

      <SliceWavePreview frameIds={previewFrameIds} mode={runMode} />

      <SlicePresetsBar
        disabled={busy}
        userPresets={userPresets}
        canSavePreset={multiMode && selected.size > 0}
        onSavePreset={saveCustomPreset}
        onDeleteUserPreset={removeUserPreset}
        chainButtons={PRESET_CHAINS.map((chain) => ({
          id: chain.id,
          label: chain.label,
          onRun: () => void runPresetChain(chain.id),
        }))}
        userChains={userChains}
        onRunUserChain={(chain) => void runUserChain(chain)}
        onDeleteUserChain={removeUserChain}
        chainBuilderMode={chainBuilderMode}
        onToggleChainBuilder={() => {
          setChainBuilderMode((m) => {
            if (m) {
              setChainDraftIds([]);
              setChainDispatchDraft(false);
            }
            return !m;
          });
        }}
        chainDraftIds={chainDraftIds}
        onToggleChainPreset={toggleChainPreset}
        onSaveChain={saveCustomChain}
        canSaveChain={chainDraftIds.length >= 2}
        chainDispatchAfter={chainDispatchDraft}
        onToggleChainDispatch={() => setChainDispatchDraft((d) => !d)}
        onExportPresets={exportPresets}
        onImportPresets={importPresets}
        onExportChains={exportChains}
        onImportChains={importChains}
        onSelect={(preset) => void runPreset(preset)}
      />

      {squadFrameProgress && busy ? (
        <div className="space-y-1" data-testid="squad-frame-run-progress">
          <div className="flex justify-between text-[10px] text-muted-foreground">
            <span>
              Squads {squadFrameProgress.completedSquads}/{squadFrameProgress.totalSquads} · Frames{" "}
              {squadFrameProgress.completedFrames}/{squadFrameProgress.totalFrames}
            </span>
            <span>{squadFrameProgress.percent}%</span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-secondary">
            <div
              className="h-full rounded-full bg-primary transition-all duration-300"
              style={{ width: `${squadFrameProgress.percent}%` }}
            />
          </div>
        </div>
      ) : null}

      <div className="flex flex-wrap gap-2">
        {busy ? (
          <Button
            size="sm"
            variant="destructive"
            onClick={cancelRun}
            data-testid="cancel-slice-run"
          >
            <XCircle className="h-4 w-4" />
            Cancel
          </Button>
        ) : null}
        <Button
          size="sm"
          disabled={busy}
          onClick={() => void runParallel("all_six")}
          data-testid="run-all-six-slices"
        >
          <Play className="h-4 w-4" />
          Run all 6
        </Button>
        <Button
          size="sm"
          variant="secondary"
          disabled={busy}
          onClick={() => void runParallel("six_squads")}
          data-testid="run-six-dispatch-squads"
        >
          <Rocket className="h-4 w-4" />
          6 + squads
        </Button>
        <Button
          size="sm"
          variant="outline"
          disabled={busy || selected.size === 0}
          onClick={() => void runParallel("selected")}
          data-testid="run-selected-slices"
        >
          <Layers className="h-4 w-4" />
          Run {selected.size || "selected"}
        </Button>
        {failedCount > 0 ? (
          <Button
            size="sm"
            variant="secondary"
            disabled={busy}
            onClick={() => void retryFailed()}
            data-testid="retry-failed-slices"
          >
            <RefreshCw className="h-4 w-4" />
            Retry failed ({failedCount})
          </Button>
        ) : null}
        {resultRows.length > 0 ? (
          <Button size="sm" variant="ghost" onClick={() => setResultsOpen(true)}>
            Results
          </Button>
        ) : null}
        <Button
          size="sm"
          variant="ghost"
          disabled={busy}
          onClick={() => setHistoryOpen(true)}
          data-testid="slice-run-history"
        >
          <History className="h-4 w-4" />
          History
        </Button>
        <Button size="sm" variant="ghost" disabled={busy} onClick={() => void reload()}>
          <RefreshCw className="h-4 w-4" />
        </Button>
        <Button
          size="sm"
          variant={multiMode ? "default" : "outline"}
          onClick={() => setMultiMode((m) => !m)}
          data-testid="toggle-multi-select"
        >
          {multiMode ? <CheckSquare className="h-4 w-4" /> : <Square className="h-4 w-4" />}
          Multi
        </Button>
        {queueDepth > 0 ? (
          <>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setQueueOpen(true)}
              data-testid="open-slice-run-queue"
            >
              <ListPlus className="h-4 w-4" />
              Queue ({queueDepth})
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={clearRunQueue}
              data-testid="clear-slice-run-queue"
            >
              Clear queue
            </Button>
          </>
        ) : null}
      </div>

      {squads.length > 0 ? (
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Squad slices — Run or Dispatch per crew
            </p>
            <Button
              size="sm"
              variant="ghost"
              disabled={busy}
              onClick={() => void dispatchAllSquadsOnly()}
              data-testid="dispatch-all-squads"
            >
              <Send className="h-3.5 w-3.5" />
              Dispatch all
            </Button>
            {squads.length > 1 ? (
              <>
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={busy}
                  onClick={() => void runAllSquads()}
                  data-testid="run-all-squads"
                >
                  <Layers className="h-3.5 w-3.5" />
                  Run all squads
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={busy}
                  onClick={() => void runAllSquadsDispatch()}
                  data-testid="run-all-squads-dispatch"
                >
                  <Send className="h-3.5 w-3.5" />
                  All squads + dispatch
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={busy}
                  onClick={() => void runAllSquadsSequential(false)}
                  data-testid="run-all-squads-sequential"
                >
                  <ListOrdered className="h-3.5 w-3.5" />
                  Sequential
                </Button>
              </>
            ) : null}
          </div>
          <div className="flex gap-2 overflow-x-auto pb-1 snap-x">
            {squadSlices.map((squad) => (
              <Card
                key={squad.squadId}
                className={cn(
                  "min-w-[150px] shrink-0 snap-start border-border/80 transition-colors",
                  activeSquadId === squad.squadId && "border-primary ring-1 ring-primary/40",
                )}
                data-testid={`squad-slice-${squad.squadId}`}
              >
                <CardHeader className="p-3 pb-2">
                  <CardTitle className="text-sm">{squad.name}</CardTitle>
                  <CardDescription className="text-xs">
                    {squad.channel} · {squadWarmLabel(squad)}
                  </CardDescription>
                </CardHeader>
                <CardContent className="flex gap-1 p-3 pt-0">
                  <Button
                    size="sm"
                    variant="secondary"
                    className="h-8 flex-1 text-xs"
                    disabled={busy}
                    onClick={() => void runSquadSlice(squad, false)}
                    data-testid={`squad-run-${squad.squadId}`}
                  >
                    <Play className="h-3 w-3" />
                    Run
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-8 flex-1 text-xs"
                    disabled={busy}
                    onClick={() => void runSquadSlice(squad, true)}
                    data-testid={`squad-dispatch-${squad.squadId}`}
                  >
                    <Send className="h-3 w-3" />
                    Dispatch
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      ) : null}

      <div
        className="grid grid-cols-2 gap-2 sm:grid-cols-3"
        data-testid="agent-slice-grid"
        aria-label="Agent slices"
      >
        {agentSlices.map((slice) => (
          <AgentSliceTile
            key={slice.agentId}
            slice={slice}
            multiMode={multiMode}
            busy={busy}
            focusFrameId={focusFrameId}
            onTap={onSliceTap}
            onLongPressDispatch={(s) => void dispatchSliceSquads(s)}
          />
        ))}
      </div>

      <Card className="border-border/60 bg-card/50">
        <CardContent className="p-3 text-sm text-muted-foreground" role="status">
          {status}
        </CardContent>
      </Card>

      <p className="text-xs text-muted-foreground">
        {runMode === "parallel"
          ? "Parallel: all slices at once. "
          : runMode === "wave"
            ? "Wave: 2 slices per batch. "
            : "Stagger: one slice at a time. "}
        {multiMode
          ? "Multi-select then Run selected or Save preset."
          : "Tap slice to run (1-6). Chain mode: tap presets in order, Save chain. Queue while busy. R retry · Esc cancel."}
      </p>

      <SliceResultsDrawer
        open={resultsOpen}
        onOpenChange={setResultsOpen}
        rows={resultRows}
        summary={lastPayload?.spoken_summary}
        onRetryFailed={failedCount > 0 && !busy ? () => void retryFailed() : undefined}
      />

      <SliceQueueDrawer
        open={queueOpen}
        onOpenChange={setQueueOpen}
        items={queueSnapshot}
        busy={busy}
        onRemove={removeFromQueue}
        onBump={bumpInQueue}
        onMove={moveInQueue}
        onClear={() => {
          clearRunQueue();
          setQueueOpen(false);
        }}
      />

      <SliceRunHistoryDrawer
        open={historyOpen}
        onOpenChange={setHistoryOpen}
        entries={historyLog}
        onRerun={rerunFromHistory}
        rerunDisabled={busy}
        onExport={exportHistory}
        onImport={importHistory}
        onClear={() => {
          clearSliceRunLog();
          setHistoryLog([]);
        }}
      />
    </div>
  );
}