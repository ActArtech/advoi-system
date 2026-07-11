"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Layers, Play, Rocket, RefreshCw, CheckSquare, Square } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  buildAgentSlices,
  buildSquadSlices,
  countSlicesByPhase,
  resolveOrchestrateFrameIds,
  squadMembershipMap,
  squadWarmLabel,
} from "@/lib/agents/agentSlices";
import {
  fetchAgents,
  fetchFrames,
  fetchSquads,
  runFrameSliceParallel,
  runSingleFrame,
  runSixParallel,
} from "@/lib/agents/orchestrateClient";
import type { AgentSliceModel, FrameRunResult, OrchestratePayload } from "@/lib/agents/types";
import { RUN_FRAME_EVENT } from "@/components/pwaOnboarding";
import { cn } from "@/lib/utils";

const PHASE_STYLES: Record<AgentSliceModel["phase"], string> = {
  idle: "border-border/70",
  queued: "border-amber-500/50 bg-amber-500/5",
  running: "border-primary animate-pulse bg-primary/10",
  ok: "border-emerald-500/50 bg-emerald-500/5",
  error: "border-destructive/60 bg-destructive/10",
};

export function AgentsOrchestrator() {
  const [agents, setAgents] = useState<Awaited<ReturnType<typeof fetchAgents>>>([]);
  const [frames, setFrames] = useState<Awaited<ReturnType<typeof fetchFrames>>>([]);
  const [squads, setSquads] = useState<Awaited<ReturnType<typeof fetchSquads>>>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [multiMode, setMultiMode] = useState(false);
  const [busy, setBusy] = useState(false);
  const [runningFrames, setRunningFrames] = useState<Set<string>>(new Set());
  const [lastResults, setLastResults] = useState<FrameRunResult[]>([]);
  const [status, setStatus] = useState("Load agents to run parallel slices.");
  const [lastPayload, setLastPayload] = useState<OrchestratePayload | null>(null);

  const reload = useCallback(async () => {
    try {
      const [a, f, s] = await Promise.all([fetchAgents(), fetchFrames(), fetchSquads()]);
      setAgents(a);
      setFrames(f);
      setSquads(s);
      const warm = a.filter((x) => x.cached).length;
      setStatus(`Ready · ${warm}/${a.length || 6} agents warm · ${s.length} squads`);
    } catch {
      setStatus("Could not load agents. Is the API up?");
    }
  }, []);

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
        results: lastResults,
        squadByAgent: squadMap,
      }),
    [agents, frames, selected, runningFrames, lastResults, squadMap],
  );

  const squadSlices = useMemo(() => buildSquadSlices(squads, agents), [squads, agents]);
  const phaseCounts = useMemo(() => countSlicesByPhase(agentSlices), [agentSlices]);

  const toggleSelect = (agentId: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(agentId)) next.delete(agentId);
      else next.add(agentId);
      return next;
    });
  };

  const applyOrchestrateResult = (data: OrchestratePayload, frameIds: string[]) => {
    setLastPayload(data);
    setLastResults(data.results ?? []);
    setRunningFrames(new Set());
    const squadNote =
      data.squads?.dispatched != null
        ? ` · Squads ${data.squads.dispatched}/${data.squads.total}`
        : "";
    setStatus((data.spoken_summary || "Parallel run complete.") + squadNote);
    void reload();
  };

  const runParallel = useCallback(
    async (mode: "selected" | "all_six" | "six_squads") => {
      if (busy) return;
      const frameIds = resolveOrchestrateFrameIds(agentSlices, mode === "selected" ? "selected" : "all_six");
      setBusy(true);
      setRunningFrames(new Set(frameIds));
      setStatus(
        mode === "six_squads"
          ? `Running ${frameIds.length} slices + dispatching squads...`
          : `Running ${frameIds.length} agent slices in parallel...`,
      );
      try {
        const data =
          mode === "six_squads"
            ? await runSixParallel({ dispatchSquads: true, refresh: true })
            : mode === "all_six"
              ? await runSixParallel({ refresh: true })
              : await runFrameSliceParallel(frameIds, { refresh: true });
        applyOrchestrateResult(data, frameIds);
      } catch (err) {
        setRunningFrames(new Set());
        setStatus(err instanceof Error ? err.message : "Parallel run failed");
      } finally {
        setBusy(false);
      }
    },
    [agentSlices, busy],
  );

  const runOneSlice = useCallback(
    async (slice: AgentSliceModel) => {
      if (busy) return;
      setBusy(true);
      setRunningFrames(new Set([slice.frameId]));
      setStatus(`Running ${slice.shortLabel}...`);
      try {
        const data = await runSingleFrame(slice.frameId, { refresh: true, confirmed: true });
        setLastResults([
          {
            frame_id: slice.frameId,
            agent_id: slice.agentId,
            status: data.status ?? "ok",
            spoken_summary: data.spoken_summary,
          },
        ]);
        setRunningFrames(new Set());
        setStatus(data.spoken_summary || `${slice.label} done.`);
        void reload();
      } catch (err) {
        setRunningFrames(new Set());
        setStatus(err instanceof Error ? err.message : "Slice run failed");
      } finally {
        setBusy(false);
      }
    },
    [busy, reload],
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
      </div>

      <div className="flex flex-wrap gap-2">
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
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Squad slices
          </p>
          <div className="flex gap-2 overflow-x-auto pb-1 snap-x">
            {squadSlices.map((squad) => (
              <Card
                key={squad.squadId}
                className="min-w-[140px] shrink-0 snap-start border-border/80"
                data-testid={`squad-slice-${squad.squadId}`}
              >
                <CardHeader className="p-3 pb-1">
                  <CardTitle className="text-sm">{squad.name}</CardTitle>
                  <CardDescription className="text-xs">
                    {squad.channel} · {squadWarmLabel(squad)}
                  </CardDescription>
                </CardHeader>
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
            disabled={busy && slice.phase !== "running"}
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
                : slice.lastStatus
                  ? slice.lastStatus
                  : slice.warm
                    ? "warm"
                    : "tap to run"}
            </p>
          </button>
        ))}
      </div>

      <Card className="border-border/60 bg-card/50">
        <CardContent className="p-3 text-sm text-muted-foreground" role="status">
          {status}
        </CardContent>
      </Card>

      <p className="text-xs text-muted-foreground">
        {multiMode
          ? "Multi-select: tap slices, then Run selected for parallel orchestrate."
          : "Tap a slice to run one frame. Swipe Voice tab for mic + operators."}
      </p>
    </div>
  );
}