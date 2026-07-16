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
import { Button } from "@/components/ui/button";
import styles from "@/components/agents/agentsTheme.module.css";
import { AgentSliceTile } from "@/components/agents/AgentSliceTile";
import { SliceQuickPicksBar } from "@/components/agents/SliceQuickPicksBar";
import { SliceFollowUpBanner } from "@/components/agents/SliceFollowUpBanner";
import { SlicePresetsBar } from "@/components/agents/SlicePresetsBar";
import { SliceResultsDrawer } from "@/components/agents/SliceResultsDrawer";
import { SliceQueueDrawer } from "@/components/agents/SliceQueueDrawer";
import { SliceRunHistoryDrawer } from "@/components/agents/SliceRunHistoryDrawer";
import { SliceWavePreview } from "@/components/agents/SliceWavePreview";
import {
  activeWaveLabels,
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
import {
  readAutoRunQueue,
  readPreferredRunMode,
  saveAutoRunQueue,
  savePreferredRunMode,
} from "@/lib/agents/slicePreferences";
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
import { allPresetsForBar, presetById } from "@/lib/agents/slicePresets";
import {
  agentIdsForQuickPick,
  quickPickById,
} from "@/lib/agents/sliceQuickPicks";
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
import { useProjectContext } from "@/components/shell/ProjectContext";
import { filterSquadsForVenture } from "@/lib/portfolio/projectModel";
import type { SquadRow } from "@/lib/agents/types";
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
  reorderQueueItem,
  type SliceQueueEntry,
  type SliceQueueItem,
} from "@/lib/agents/sliceRunQueue";
import {
  describeBundleImport,
  exportOrchestrationBundle,
  parseOrchestrationImport,
} from "@/lib/agents/sliceOrchestrationBundle";
import {
  labelsForChainPlan,
  resolveBuiltinChainPlan,
  resolveUserChainPlan,
} from "@/lib/agents/sliceChainStack";
import {
  postRunFollowUps,
  type SliceFollowUp,
} from "@/lib/agents/slicePostRunSuggestions";
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
  const projectCtx = useProjectContext();
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
  const [followUps, setFollowUps] = useState<SliceFollowUp[]>([]);
  const [followUpTitle, setFollowUpTitle] = useState("");
  const [autoRunQueue, setAutoRunQueue] = useState(false);

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
        setFollowUpTitle(
          failed
            ? "Voice sync failed — retry or continue?"
            : "Morning pulse synced — continue with a multi-agent chain?",
        );
        setFollowUps(
          postRunFollowUps([frameId], failed ? 1 : 0, {
            queueDepth: runQueueRef.current.length,
          }),
        );
      } else {
        setStatus(`Voice sync complete: ${frameId}`);
        setFollowUps([]);
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
    setAutoRunQueue(readAutoRunQueue());
    setHistoryLog(readSliceRunLog());
    setUserPresets(readUserPresets());
    setUserChains(readUserChains());
    void reload();
    const t = window.setInterval(() => void reload(), 20_000);
    return () => window.clearInterval(t);
  }, [reload]);

  const scopedSquads = useMemo(
    () =>
      filterSquadsForVenture<SquadRow>(
        squads,
        projectCtx?.activeVentureId,
        projectCtx?.activeVenture?.squads,
      ),
    [squads, projectCtx?.activeVentureId, projectCtx?.activeVenture?.squads],
  );

  const scopedFrames = useMemo(() => {
    const ventureFrames = projectCtx?.activeVenture?.functions
      .filter((row) => row.kind === "frame" && row.frame_id)
      .map((row) => row.frame_id as string);
    if (!ventureFrames || ventureFrames.length === 0) return frames;
    const allowed = new Set(ventureFrames);
    const filtered = frames.filter((row) => allowed.has(row.id));
    return filtered.length > 0 ? filtered : frames;
  }, [frames, projectCtx?.activeVenture]);

  const squadMap = useMemo(() => squadMembershipMap(scopedSquads), [scopedSquads]);

  const agentSlices = useMemo(
    () =>
      buildAgentSlices(agents, scopedFrames, {
        selectedIds: selected,
        runningFrameIds: runningFrames,
        queuedFrameIds: queuedFrames,
        results: lastResults,
        squadByAgent: squadMap,
      }),
    [agents, scopedFrames, selected, runningFrames, queuedFrames, lastResults, squadMap],
  );

  const squadSlices = useMemo(
    () => buildSquadSlices(scopedSquads, agents),
    [scopedSquads, agents],
  );
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

  const stackBatch = useCallback(
    (label: string, runFn: () => Promise<void>) => {
      runQueueRef.current = enqueueSliceRun(
        runQueueRef.current,
        createQueueEntry(label, runFn),
      );
      syncQueueUi();
      setStatus(`Stacked "${label}" · ${runQueueRef.current.length} in queue`);
    },
    [syncQueueUi],
  );

  const runQueueNow = useCallback(() => {
    if (busy || runQueueRef.current.length === 0) return;
    processRunQueue();
  }, [busy, processRunQueue]);

  const maybeAutoStartQueue = useCallback(() => {
    if (autoRunQueue && !busy && runQueueRef.current.length > 0) {
      processRunQueue();
    }
  }, [autoRunQueue, busy, processRunQueue]);

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

  const reorderInQueue = useCallback(
    (id: string, toIndex: number) => {
      runQueueRef.current = reorderQueueItem(runQueueRef.current, id, toIndex);
      syncQueueUi();
      setStatus("Reordered queue.");
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
    setFollowUpTitle(
      failCount > 0
        ? "Some slices failed — retry or continue?"
        : frameIds.length > 0
          ? "Batch complete — run a follow-up chain?"
          : "",
    );
    const squadsDispatched =
      data.squads?.dispatched != null && data.squads.dispatched > 0;
    if (frameIds.length > 0 || failCount > 0) {
      setFollowUps(
        postRunFollowUps(frameIds, failCount, {
          queueDepth: runQueueRef.current.length,
          squadsDispatched,
        }),
      );
    } else if (runQueueRef.current.length > 0) {
      setFollowUpTitle("Queue ready — start the next batch?");
      setFollowUps(
        postRunFollowUps([], 0, { queueDepth: runQueueRef.current.length }),
      );
    } else {
      setFollowUps([]);
    }
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

  const stackPresetChain = useCallback(
    (chainId: string) => {
      const plan = resolveBuiltinChainPlan(chainId);
      if (!plan) return;
      const labels = labelsForChainPlan(plan);
      plan.stages.forEach((stage, index) => {
        const label = labels[index] ?? `${plan.chainLabel}: ${stage.label}`;
        stackBatch(label, () =>
          runWithPlanInternal([...stage.preset.frameIds], stage.preset.mode, label),
        );
      });
      if (plan.dispatchAfter) {
        const dispatchLabel = labels[labels.length - 1] ?? `${plan.chainLabel}: Dispatch`;
        stackBatch(dispatchLabel, () => dispatchAllSquadsInternal());
      }
      maybeAutoStartQueue();
    },
    [stackBatch, runWithPlanInternal, dispatchAllSquadsInternal, maybeAutoStartQueue],
  );

  const stackUserChain = useCallback(
    (chain: UserPresetChain) => {
      const plan = resolveUserChainPlan(chain, userPresets);
      if (!plan) return;
      const labels = labelsForChainPlan(plan);
      plan.stages.forEach((stage, index) => {
        const label = labels[index] ?? `${plan.chainLabel}: ${stage.label}`;
        stackBatch(label, () =>
          runWithPlanInternal([...stage.preset.frameIds], stage.preset.mode, label),
        );
      });
      if (plan.dispatchAfter) {
        const dispatchLabel = labels[labels.length - 1] ?? `${plan.chainLabel}: Dispatch`;
        stackBatch(dispatchLabel, () => dispatchAllSquadsInternal());
      }
      maybeAutoStartQueue();
    },
    [userPresets, stackBatch, runWithPlanInternal, dispatchAllSquadsInternal, maybeAutoStartQueue],
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

  const runSelectedStagger = useCallback(() => {
    const frameIds = resolveOrchestrateFrameIds(
      agentSlices,
      selected.size > 0 ? "selected" : "all_six",
    );
    runWithPlan(frameIds, "stagger", selected.size > 0 ? "Selected stagger" : "All six stagger");
  }, [agentSlices, selected.size, runWithPlan]);

  const applyQuickPick = useCallback(
    (pickId: string) => {
      const pick = quickPickById(pickId);
      if (!pick) return;
      if (pick.action === "clear") {
        setSelected(new Set());
        setStatus("Selection cleared");
        return;
      }
      const ids = agentIdsForQuickPick(pick, agentSlices);
      setSelected(new Set(ids));
      setMultiMode(true);
      setStatus(`Selected ${ids.length} slice${ids.length === 1 ? "" : "s"} (${pick.label})`);
    },
    [agentSlices],
  );

  const selectAllSlices = useCallback(() => {
    setMultiMode(true);
    setSelected(new Set(agentSlices.map((s) => s.agentId)));
    setStatus(`Selected all ${agentSlices.length} slices`);
  }, [agentSlices]);

  const stackSelectedBatch = useCallback(() => {
    const scope = selected.size > 0 ? "selected" : "all_six";
    const label = scope === "selected" ? `Selected (${selected.size})` : "All six";
    stackBatch(label, () => runParallelInternal(scope));
    maybeAutoStartQueue();
  }, [selected.size, stackBatch, runParallelInternal, maybeAutoStartQueue]);

  const runQuickPick = useCallback(
    (pickId: string) => {
      const pick = quickPickById(pickId);
      if (!pick || pick.action === "clear") return;
      if (pick.action === "all") {
        void runParallel("all_six");
        return;
      }
      if (pick.presetId) {
        const preset = presetById(pick.presetId);
        if (preset) runPreset(preset);
      }
    },
    [runParallel, runPreset],
  );

  const stackQuickPick = useCallback(
    (pickId: string) => {
      const pick = quickPickById(pickId);
      if (!pick || pick.action === "clear") return;
      if (pick.action === "all") {
        stackBatch("All six", () => runParallelInternal("all_six"));
        maybeAutoStartQueue();
        return;
      }
      if (pick.presetId) {
        const preset = presetById(pick.presetId);
        if (!preset) return;
        stackBatch(preset.label, () =>
          runWithPlanInternal([...preset.frameIds], preset.mode, preset.label),
        );
        maybeAutoStartQueue();
      }
    },
    [stackBatch, runParallelInternal, runWithPlanInternal, maybeAutoStartQueue],
  );

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

  const bundleFilePicker = useJsonFilePicker({
    onJson: (raw) => {
      try {
        const result = parseOrchestrationImport(raw);
        if (result.importedSections.includes("presets")) {
          setUserPresets(result.presets);
        }
        if (result.importedSections.includes("chains")) {
          setUserChains(result.chains);
        }
        if (result.importedSections.includes("history")) {
          setHistoryLog(result.history);
        }
        if (result.runMode) {
          setRunMode(result.runMode);
          savePreferredRunMode(result.runMode);
        }
        setStatus(describeBundleImport(result.importedSections));
      } catch {
        setStatus("Invalid orchestration bundle JSON");
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

  const executeFollowUp = useCallback(
    (followUp: SliceFollowUp) => {
      setFollowUps([]);
      switch (followUp.action.kind) {
        case "run_chain":
          void runPresetChain(followUp.action.chainId);
          break;
        case "stack_chain":
          stackPresetChain(followUp.action.chainId);
          break;
        case "run_queue":
          runQueueNow();
          break;
        case "dispatch_all":
          void dispatchAllSquadsOnly();
          break;
        case "retry_stagger": {
          const frameIds = frameIdsFromFailedResults(lastResults);
          if (frameIds.length > 0) {
            runWithPlan(frameIds, "stagger", "Retry failed");
          }
          break;
        }
      }
    },
    [
      runPresetChain,
      stackPresetChain,
      runQueueNow,
      dispatchAllSquadsOnly,
      lastResults,
      runWithPlan,
    ],
  );

  const runPrimaryFollowUp = useCallback(() => {
    const primary = followUps[0];
    if (!primary) return;
    executeFollowUp(primary);
  }, [followUps, executeFollowUp]);

  const runSecondaryFollowUp = useCallback(() => {
    const secondary = followUps[1];
    if (!secondary) return;
    executeFollowUp(secondary);
  }, [followUps, executeFollowUp]);

  useSliceKeyboard({
    slices: agentSlices,
    busy,
    failedCount,
    selectedCount: selected.size,
    multiMode,
    followUpCount: followUps.length,
    queueDepth,
    onRunSlice: runOneSlice,
    onRetryFailed: retryFailed,
    onCancel: cancelRun,
    onToggleMulti: () => setMultiMode((m) => !m),
    onRunAll: () => void runParallel("all_six"),
    onRunSelected: () => void runParallel("selected"),
    onRunSelectedStagger: () => void runSelectedStagger(),
    onRunPrimaryFollowUp: runPrimaryFollowUp,
    onRunSecondaryFollowUp: runSecondaryFollowUp,
    onStackSelected: stackSelectedBatch,
    onRunQueue: runQueueNow,
    onOpenQueue: () => setQueueOpen(true),
    onOpenHistory: () => setHistoryOpen(true),
    onSelectAll: selectAllSlices,
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

  const exportBundle = useCallback(() => {
    downloadJsonFile(
      "advoi-orchestration-bundle.json",
      exportOrchestrationBundle({
        presets: userPresets,
        chains: userChains,
        history: historyLog,
        runMode,
      }),
    );
    setStatus("Orchestration bundle exported");
  }, [userPresets, userChains, historyLog, runMode]);

  const importBundle = useCallback(() => {
    bundleFilePicker.openPicker();
  }, [bundleFilePicker]);

  const followUpHint =
    followUps.length > 0
      ? `C ${followUps[0]?.label}${followUps[1] ? ` · Shift+C ${followUps[1].label}` : ""}${queueDepth > 0 ? " · Y run queue" : ""}`
      : queueDepth > 0
        ? "Y run queue"
        : undefined;

  const warmCount = agents.filter((a) => a.cached).length;
  const totalAgents = agents.length || 6;
  const activeWave = busy && runningFrames.size > 0 ? activeWaveLabels(runningFrames) : null;

  return (
    <div className={cn("stagger-children", styles.root)} data-testid="agents-orchestrator" data-ui-version="v2">
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
      <input
        ref={bundleFilePicker.inputRef}
        type="file"
        accept="application/json,.json"
        className="sr-only"
        aria-hidden
        tabIndex={-1}
        onChange={bundleFilePicker.onChange}
        data-testid="import-bundle-file-input"
      />
      <div className={cn(styles.panel, styles.panelBodyFlush)}>
        <div className={styles.statusStrip}>
          <span
            className={cn(
              styles.stateChip,
              warmCount === totalAgents && styles.stateChipWarm,
            )}
          >
            {warmCount}/{totalAgents} warm
          </span>
          {busy ? <span className={cn(styles.stateChip, styles.stateChipRunning)}>Running</span> : null}
          {lastPayload?.squads?.dispatched != null ? (
            <span className={styles.stateChip}>
              Squads {lastPayload.squads.dispatched}/{lastPayload.squads.total}
            </span>
          ) : null}
          {phaseCounts.running > 0 ? (
            <span className={cn(styles.stateChip, styles.stateChipRunning)} data-testid="active-slice-count">
              {phaseCounts.running} running
            </span>
          ) : null}
          {busy && runningFrames.size > 0 ? (
            <span className={styles.stateChip} data-testid="concurrent-frame-count">
              {runningFrames.size} active
            </span>
          ) : null}
          {activeWave ? (
            <span className={styles.activeWaveChip} data-testid="active-wave-labels">
              Now: {activeWave}
            </span>
          ) : null}
          {phaseCounts.queued > 0 ? (
            <span className={styles.stateChip}>{phaseCounts.queued} queued</span>
          ) : null}
          {squadProgress && busy ? (
            <span className={styles.stateChip} data-testid="squad-run-progress">
              Squads {squadProgress.done}/{squadProgress.total}
            </span>
          ) : null}
          {queueDepth > 0 ? (
            <button
              type="button"
              className={cn(styles.stateChip, styles.stateChipQueue)}
              onClick={() => setQueueOpen(true)}
              data-testid="slice-run-queue-depth"
            >
              Queue: {queueDepth} waiting
            </button>
          ) : null}
        </div>
        {progress && busy ? (
          <div className="mt-3 space-y-1" data-testid="slice-run-progress">
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>
                Wave {Math.min(progress.waveIndex + 1, progress.waveCount)}/{progress.waveCount}
              </span>
              <span>{progress.percent}%</span>
            </div>
            <div className={styles.progressTrack}>
              <div className={styles.progressFill} style={{ width: `${progress.percent}%` }} />
            </div>
          </div>
        ) : null}
      </div>

      <div className={cn(styles.panel, styles.panelAccent)}>
        <div className={styles.panelHeader}>
          <h3 className={styles.panelTitle}>Six agent slices</h3>
          <p className={styles.panelDesc}>
            Tap to run · keys 1-6 · hold tile to dispatch squads
            {multiMode ? " · multi-select on" : ""}
          </p>
        </div>
        <div className={styles.panelBody}>
          <SliceQuickPicksBar
            disabled={busy}
            onPick={applyQuickPick}
            onRunPick={runQuickPick}
            onStackPick={stackQuickPick}
          />
          <div className={styles.sliceGrid} data-testid="agent-slice-grid" aria-label="Agent slices">
            {agentSlices.map((slice, index) => (
              <AgentSliceTile
                key={slice.agentId}
                slice={slice}
                index={index}
                multiMode={multiMode}
                busy={busy}
                focusFrameId={focusFrameId}
                onTap={onSliceTap}
                onLongPressDispatch={(s) => void dispatchSliceSquads(s)}
              />
            ))}
          </div>
        </div>
      </div>

      <div className={styles.panel}>
        <div className={styles.panelHeader}>
          <h3 className={styles.panelTitle}>Quick actions</h3>
        </div>
        <div className={cn(styles.panelBody, styles.actionRow)}>
          {busy ? (
            <Button size="sm" variant="destructive" onClick={cancelRun} data-testid="cancel-slice-run">
              <XCircle className="h-4 w-4" />
              Cancel
            </Button>
          ) : null}
          <button
            type="button"
            disabled={busy}
            onClick={() => void runParallel("all_six")}
            data-testid="run-all-six-slices"
            className={styles.ctaPrimary}
          >
            <Play className="h-4 w-4" />
            Run all 6
          </button>
          <Button
            size="default"
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
          <Button
            size="sm"
            variant="outline"
            disabled={busy}
            onClick={() => void runSelectedStagger()}
            data-testid="run-selected-stagger"
          >
            <ListOrdered className="h-4 w-4" />
            Stagger
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={busy}
            onClick={stackSelectedBatch}
            data-testid="stack-selected-batch"
          >
            <ListPlus className="h-4 w-4" />
            Stack queue
          </Button>
          <Button
            size="sm"
            variant={autoRunQueue ? "default" : "outline"}
            disabled={busy}
            onClick={() => {
              const next = !autoRunQueue;
              setAutoRunQueue(next);
              saveAutoRunQueue(next);
              setStatus(next ? "Auto-run queue on" : "Auto-run queue off");
            }}
            data-testid="toggle-auto-run-queue"
          >
            <Play className="h-4 w-4" />
            Auto-run
          </Button>
          {!busy && queueDepth > 0 ? (
            <button
              type="button"
              className={styles.ctaPrimary}
              onClick={runQueueNow}
              data-testid="run-queue-now"
            >
              <Play className="h-4 w-4" />
              Run queue ({queueDepth})
            </button>
          ) : null}
          {failedCount > 0 ? (
            <Button size="sm" variant="secondary" disabled={busy} onClick={() => void retryFailed()} data-testid="retry-failed-slices">
              <RefreshCw className="h-4 w-4" />
              Retry ({failedCount})
            </Button>
          ) : null}
          {resultRows.length > 0 ? (
            <Button size="sm" variant="outline" onClick={() => setResultsOpen(true)}>
              Results
            </Button>
          ) : null}
          <Button size="sm" variant="outline" disabled={busy} onClick={() => setHistoryOpen(true)} data-testid="slice-run-history">
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
              <Button size="sm" variant="secondary" onClick={() => setQueueOpen(true)} data-testid="open-slice-run-queue">
                <ListPlus className="h-4 w-4" />
                Queue ({queueDepth})
              </Button>
              <Button size="sm" variant="ghost" onClick={clearRunQueue} data-testid="clear-slice-run-queue">
                Clear queue
              </Button>
            </>
          ) : null}
        </div>
      </div>

      <div className={styles.panel}>
        <div className={styles.panelHeader}>
          <h3 className={styles.panelTitle}>Run mode</h3>
          <p className={styles.panelDesc}>How slices execute when you run a batch</p>
        </div>
        <div className={cn(styles.panelBody, "space-y-3")}>
          <div className={styles.modeRow} role="group" aria-label="Run mode">
            {MODE_OPTIONS.map(({ mode, label, icon: Icon }) => (
              <button
                key={mode}
                type="button"
                disabled={busy}
                onClick={() => {
                  setRunMode(mode);
                  savePreferredRunMode(mode);
                }}
                data-testid={`run-mode-${mode}`}
                className={cn(styles.modeBtn, runMode === mode && styles.modeBtnActive)}
              >
                <Icon className="h-4 w-4" />
                {label}
              </button>
            ))}
          </div>
          <SliceWavePreview frameIds={previewFrameIds} mode={runMode} />
        </div>
      </div>

      {followUps.length > 0 && !busy ? (
        <SliceFollowUpBanner
          title={followUpTitle}
          followUps={followUps}
          disabled={busy}
          onExecute={executeFollowUp}
          onDismiss={() => setFollowUps([])}
          hint={followUpHint}
          testId="slice-follow-up-banner"
        />
      ) : null}

      <div className={styles.panel}>
        <div className={styles.panelHeader}>
          <h3 className={styles.panelTitle}>Presets & chains</h3>
          <p className={styles.panelDesc}>One-tap batches and multi-stage sequences</p>
        </div>
        <div className={styles.panelBody}>
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
          onStack: () => stackPresetChain(chain.id),
        }))}
        userChains={userChains}
        onRunUserChain={(chain) => void runUserChain(chain)}
        onStackUserChain={(chain) => stackUserChain(chain)}
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
        onExportBundle={exportBundle}
        onImportBundle={importBundle}
        onSelect={(preset) => void runPreset(preset)}
          />
        </div>
      </div>

      {squads.length > 0 ? (
        <div className={styles.panel}>
          <div className={styles.panelHeader}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <h3 className={styles.panelTitle}>Squad crews</h3>
                <p className={styles.panelDesc}>Run or dispatch per squad channel</p>
              </div>
              <div className="flex flex-wrap gap-1.5">
                <Button size="sm" variant="outline" disabled={busy} onClick={() => void dispatchAllSquadsOnly()} data-testid="dispatch-all-squads">
                  <Send className="h-3.5 w-3.5" />
                  Dispatch all
                </Button>
                {squads.length > 1 ? (
                  <>
                    <Button size="sm" variant="secondary" disabled={busy} onClick={() => void runAllSquads()} data-testid="run-all-squads">
                      <Layers className="h-3.5 w-3.5" />
                      Run all
                    </Button>
                    <Button size="sm" variant="ghost" disabled={busy} onClick={() => void runAllSquadsSequential(false)} data-testid="run-all-squads-sequential">
                      <ListOrdered className="h-3.5 w-3.5" />
                      Sequential
                    </Button>
                  </>
                ) : null}
              </div>
            </div>
            {squadFrameProgress && busy ? (
              <div className="mt-2 space-y-1" data-testid="squad-frame-run-progress">
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>
                    Squads {squadFrameProgress.completedSquads}/{squadFrameProgress.totalSquads} · Frames{" "}
                    {squadFrameProgress.completedFrames}/{squadFrameProgress.totalFrames}
                  </span>
                  <span>{squadFrameProgress.percent}%</span>
                </div>
                <div className={styles.progressTrack}>
                  <div className={styles.progressFill} style={{ width: `${squadFrameProgress.percent}%` }} />
                </div>
              </div>
            ) : null}
          </div>
          <div className={cn(styles.panelBody, styles.squadScroll)}>
            {squadSlices.map((squad) => (
              <div
                key={squad.squadId}
                className={cn(
                  styles.squadCard,
                  activeSquadId === squad.squadId && styles.squadCardActive,
                )}
                data-testid={`squad-slice-${squad.squadId}`}
              >
                <p className="text-sm font-semibold text-foreground">{squad.name}</p>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  {squad.channel} · {squadWarmLabel(squad)}
                </p>
                <div className="mt-2 flex gap-1">
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
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      <div className={styles.statusFooter} role="status">
        {status}
      </div>

      <p className={styles.hint}>
        {runMode === "parallel"
          ? "Parallel: all slices at once. "
          : runMode === "wave"
            ? "Wave: 2 slices per batch. "
            : "Stagger: one slice at a time. "}
        {multiMode
          ? "Multi-select then Run selected or Save preset."
          : "1-6 run slice · Enter batch · Shift+Enter stagger · A select all · C / Shift+C chains · Q queue · H history."}
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
        onReorder={reorderInQueue}
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