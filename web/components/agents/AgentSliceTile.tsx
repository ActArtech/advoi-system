"use client";

import { useLongPress } from "@/hooks/useLongPress";
import type { AgentSliceModel } from "@/lib/agents/types";
import { formatRelativeTimeFromValue } from "@/lib/agents/sliceRunLog";
import { cn } from "@/lib/utils";

const PHASE_STYLES: Record<AgentSliceModel["phase"], string> = {
  idle: "border-border/70",
  queued: "border-amber-500/50 bg-amber-500/5",
  running: "border-primary animate-pulse bg-primary/10",
  ok: "border-emerald-500/50 bg-emerald-500/5",
  error: "border-destructive/60 bg-destructive/10",
};

type AgentSliceTileProps = {
  slice: AgentSliceModel;
  multiMode: boolean;
  busy: boolean;
  focusFrameId: string | null;
  onTap: (slice: AgentSliceModel) => void;
  onLongPressDispatch?: (slice: AgentSliceModel) => void;
};

export function AgentSliceTile({
  slice,
  multiMode,
  busy,
  focusFrameId,
  onTap,
  onLongPressDispatch,
}: AgentSliceTileProps) {
  const longPress = useLongPress(
    () => {
      if (!busy && onLongPressDispatch && slice.squadIds.length > 0) {
        onLongPressDispatch(slice);
      }
    },
    { disabled: busy || !onLongPressDispatch || slice.squadIds.length === 0 },
  );

  return (
    <button
      type="button"
      disabled={busy && slice.phase !== "running" && slice.phase !== "queued"}
      onClick={() => {
        if (longPress.consumeLongPress()) return;
        onTap(slice);
      }}
      onPointerDown={longPress.onPointerDown}
      onPointerUp={longPress.onPointerUp}
      onPointerLeave={longPress.onPointerLeave}
      onPointerCancel={longPress.onPointerCancel}
      data-testid={`agent-slice-${slice.agentId}`}
      data-frame-id={slice.frameId}
      data-phase={slice.phase}
      data-warm={slice.warm ? "true" : "false"}
      data-squad-count={slice.squadIds.length}
      className={cn(
        "rounded-xl border p-3 text-left transition-all active:scale-[0.98]",
        "min-h-[88px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        PHASE_STYLES[slice.phase],
        slice.selected && multiMode && "ring-2 ring-primary",
        focusFrameId === slice.frameId && "ring-2 ring-amber-400 animate-pulse",
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
            : slice.phase === "idle" && slice.lastRunAt
              ? formatRelativeTimeFromValue(slice.lastRunAt)
              : slice.lastStatus
                ? slice.lastStatus
                : slice.warm
                  ? "warm"
                  : "tap run · hold dispatch"}
      </p>
      {slice.squadIds.length > 0 ? (
        <p className="mt-0.5 text-[9px] text-muted-foreground/80">
          {slice.squadIds.join(", ")}
        </p>
      ) : null}
    </button>
  );
}