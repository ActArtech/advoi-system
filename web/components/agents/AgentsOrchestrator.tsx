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
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { SliceResultsDrawer } from "@/components/agents/SliceResultsDrawer";
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
  squadWarmLabel,
} from "@/lib/agents/agentSlices";
import {
  executeAllSquadsPlan,
  executeSlicePlan,
  executeSquadSlicePlan,
} from "@/lib/agents/runPlan";
import { useSliceWaveCallbacks } from "@/lib/agents/useSliceWaveCallbacks";
import {
  fetchAgents,
  fetchFrames,
  fetchSquads,
  runSixParallel,
} from "@/lib/agents/orchestrateClient";
import type {
  AgentSliceModel,
  FrameRunResult,
  OrchestratePayload,
  RunExecutionMode,
  SliceRunProgress,
  SquadSliceModel,
} from "@/lib/agents/types";
import { RUN_FRAME_EVENT } from "@/components/pwaOnboarding";
import { cn } from "@/lib/utils";

const PHASE_STYLES: Record<AgentSliceModel["phase"], string> = {
  idle: "border-border/70",
  queued: "border-amber-500/50 bg-amber-500/5",
  running: "border-primary animate-pulse bg-primary/10",
  ok: "border-emerald-500/50 bg-emerald-500/5",
  error: "border-destructive/60 bg-destructive/10",
};

const MODE_OPTIONS: { mode: RunExecutionMode; label: string; icon: typeof Zap }[] = [
  { mode: "parallel", label: "Parallel", icon: Zap },
  { mode: "wave", label: "Wave x2", icon: Waves },
  { mode: "stagger", label: "Stagger", icon: ListOrdered },
];

export function AgentsOrchestrator() {
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
  const abortRef = useRef<AbortController | null>(null);

  const createWaveCallbacks = useSliceWaveCallbacks({
    setRunningFrames,
    setQueuedFrames,
    setProgress,
  });

  const reload = useCallback(async () => {
    try {
      const [a, f, s] = await Promise.all([fetchAgents(), fetchFrames(), fetchSquads()]);
      setAgents(a);
      setFrames(f);
      setSquads(s);
      if (!busy) {
        const warm = a.filter((x) => x.cached).length;
        setStatus(`Ready · ${warm}/${a.length || 6} warm · ${s.length} squads`);
      }
    } catch {
      if (!busy) setStatus("Could not load agents. Is the API up?");
    }
  }, [busy]);

  useEffect(() => {
    void reload();
    const onFrame = () => void reload();
    window.addEventListener(RUN_FRAME_EVENT, onFrame);
    const t = window.setInterval(() => void reload(), 20_000);
    return () => {
      window.removeEventListener(RUN_FRAME_EVENT, onFrame);
      window.clearInterval(t);
    };
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
  };

  const isAbortError = (err: unknown) =>
    err instanceof DOMException && err.name === "AbortError";

  const cancelRun = () => {
    abortRef.current?.abort();
    setBusy(false);
    resetRunUi();
    setStatus("Run cancelled.");
  };

  const finishRun = (data: OrchestratePayload, frameIds: string[]) => {
    setLastPayload(data);
    setLastResults(data.results ?? []);
    resetRunUi();
    const squadNote =
      data.squads?.dispatched != null
        ? ` · Squads ${data.squads.dispatched}/${data.squads.total}`
        : "";
    setStatus((data.spoken_summary || `Completed ${frameIds.length} slices.`) + squadNote);
    if ((data.results?.length ?? 0) > 1) setResultsOpen(true);
    void reload();
  };

  const runWithPlan = useCallback(
    async (frameIds: string[], mode: RunExecutionMode, label: string) => {
      if (busy || frameIds.length === 0) return;
      const waves = chunkFrameWaves(frameIds, mode);
      const controller = beginRun();
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
    [busy, createWaveCallbacks],
  );

  const runParallel = useCallback(
    async (scope: "selected" | "all_six" | "six_squads") => {
      if (busy) return;
      if (scope === "six_squads") {
        const frameIds = [...resolveOrchestrateFrameIds(agentSlices, "all_six")];
        const controller = beginRun();
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
      await runWithPlan(frameIds, runMode, scope === "selected" ? "Selected run" : "All six");
    },
    [agentSlices, busy, runMode, runWithPlan],
  );

  const runSquadSlice = useCallback(
    async (squad: SquadSliceModel, dispatchAfter: boolean) => {
      if (busy) return;
      const frameIds = frameIdsForSquadSlice(squad, frames);
      if (frameIds.length === 0) {
        setStatus(`No frames mapped for ${squad.name}`);
        return;
      }
      setActiveSquadId(squad.squadId);
      const waves = chunkFrameWaves(frameIds, runMode);
      const controller = beginRun();
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
    [busy, frames, runMode, createWaveCallbacks],
  );

  const runAllSquads = useCallback(async () => {
    if (busy || squads.length <= 1) return;

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
    setBusy(true);
    setLastResults([]);
    setRunningFrames(new Set(allFrameIds));
    setQueuedFrames(new Set());
    setProgress(null);
    setSquadProgress({ done: 0, total: plans.length });
    setStatus(`Running ${plans.length} squads in parallel (${allFrameIds.length} slices)...`);

    try {
      const payload = await executeAllSquadsPlan(
        plans.map(({ squad, frameIds }) => ({ squadId: squad.squadId, frameIds })),
        runMode,
        { signal: controller.signal },
        {
          onSquadStart: (squadId) => setActiveSquadId(squadId),
          onSquadDone: () => {
            setSquadProgress((prev) =>
              prev ? { ...prev, done: Math.min(prev.done + 1, prev.total) } : null,
            );
          },
        },
      );
      finishRun(payload, allFrameIds);
    } catch (err) {
      resetRunUi();
      setStatus(
        isAbortError(err) ? "Run cancelled." : err instanceof Error ? err.message : "Run all squads failed",
      );
    } finally {
      setBusy(false);
    }
  }, [busy, squads.length, squadSlices, frames, runMode]);

  const retryFailed = useCallback(async () => {
    const frameIds = frameIdsFromFailedResults(lastResults);
    if (frameIds.length === 0 || busy) return;
    await runWithPlan(frameIds, runMode, "Retry failed");
  }, [lastResults, busy, runMode, runWithPlan]);

  const runOneSlice = useCallback(
    async (slice: AgentSliceModel) => {
      await runWithPlan([slice.frameId], "stagger", slice.shortLabel);
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

  const warmCount = agents.filter((a) => a.cached).length;
  const totalAgents = agents.length || 6;

  return (
    <div className="space-y-4" data-testid="agents-orchestrator">
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
          <Badge variant="warning">{phaseCounts.running} running</Badge>
        ) : null}
        {phaseCounts.queued > 0 ? (
          <Badge variant="outline">{phaseCounts.queued} queued</Badge>
        ) : null}
        {squadProgress && busy ? (
          <Badge variant="default" data-testid="squad-run-progress">
            Squads {squadProgress.done}/{squadProgress.total}
          </Badge>
        ) : null}
      </div>

      <div className="flex flex-wrap gap-1.5" role="group" aria-label="Run mode">
        {MODE_OPTIONS.map(({ mode, label, icon: Icon }) => (
          <Button
            key={mode}
            size="sm"
            variant={runMode === mode ? "default" : "outline"}
            disabled={busy}
            onClick={() => setRunMode(mode)}
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
      </div>

      {squads.length > 0 ? (
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Squad slices — tap run, long-press dispatch
            </p>
            {squads.length > 1 ? (
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
          <button
            key={slice.agentId}
            type="button"
            disabled={busy && slice.phase !== "running" && slice.phase !== "queued"}
            onClick={() => onSliceTap(slice)}
            data-testid={`agent-slice-${slice.agentId}`}
            data-frame-id={slice.frameId}
            data-phase={slice.phase}
            data-warm={slice.warm ? "true" : "false"}
            className={cn(
              "rounded-xl border p-3 text-left transition-all active:scale-[0.98]",
              "min-h-[88px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              PHASE_STYLES[slice.phase],
              slice.selected && multiMode && "ring-2 ring-primary",
              !slice.warm && slice.phase === "idle" && "opacity-80",
            )}
          >
            <div className="flex items-start justify-between gap-1">
              <span className="text-xs font-semibold uppercase tracking-wide text-primary">
                {slice.shortLabel}
              </span>
              <span
                className={cn(
                  "h-2 w-2 shrink-0 rounded-full",
                  slice.warm ? "bg-emerald-400" : "bg-muted-foreground/40",
                )}
                aria-hidden
              />
            </div>
            <p className="mt-1 line-clamp-2 text-sm font-medium leading-tight">{slice.label}</p>
            <p className="mt-1 text-[10px] text-muted-foreground">
              {slice.phase === "running"
                ? "running..."
                : slice.phase === "queued"
                  ? "queued..."
                  : slice.lastStatus
                    ? slice.lastStatus
                    : slice.warm
                      ? "warm"
                      : "tap to run"}
            </p>
            {slice.squadIds.length > 0 ? (
              <p className="mt-0.5 text-[9px] text-muted-foreground/80">
                {slice.squadIds.join(", ")}
              </p>
            ) : null}
          </button>
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
          ? "Multi-select then Run selected."
          : "Tap slice for single run. Squad cards run that crew only."}
      </p>

      <SliceResultsDrawer
        open={resultsOpen}
        onOpenChange={setResultsOpen}
        rows={resultRows}
        summary={lastPayload?.spoken_summary}
        onRetryFailed={failedCount > 0 && !busy ? () => void retryFailed() : undefined}
      />
    </div>
  );
}