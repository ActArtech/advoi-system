"use client";

import { Badge } from "@/components/ui/badge";
import { useLongPress } from "@/hooks/useLongPress";
import type { AgentSliceModel } from "@/lib/agents/types";
import { formatRelativeTimeFromValue } from "@/lib/agents/sliceRunLog";
import { cn } from "@/lib/utils";

const PHASE_STYLES: Record<AgentSliceModel["phase"], string> = {
  idle: "border-border/70 bg-card/80",
  queued: "border-amber-500/60 bg-amber-500/10 shadow-sm shadow-amber-500/10",
  running: "border-primary bg-primary/15 shadow-md shadow-primary/20 animate-pulse",
  ok: "border-emerald-500/60 bg-emerald-500/10 shadow-sm shadow-emerald-500/10",
  error: "border-destructive/70 bg-destructive/15 shadow-sm shadow-destructive/10",
};

const PHASE_BADGE: Record<
  AgentSliceModel["phase"],
  { label: string; variant: "outline" | "warning" | "default" | "success" | "destructive" }
> = {
  idle: { label: "idle", variant: "outline" },
  queued: { label: "queued", variant: "warning" },
  running: { label: "running", variant: "default" },
  ok: { label: "ok", variant: "success" },
  error: { label: "error", variant: "destructive" },
};

type AgentSliceTileProps = {
  slice: AgentSliceModel;
  index: number;
  multiMode: boolean;
  busy: boolean;
  focusFrameId: string | null;
  onTap: (slice: AgentSliceModel) => void;
  onLongPressDispatch?: (slice: AgentSliceModel) => void;
};

export function AgentSliceTile({
  slice,
  index,
  multiMode,
  busy,
  focusFrameId,
  onTap,
  onLongPressDispatch,
}: AgentSliceTileProps) {
  const phaseBadge = PHASE_BADGE[slice.phase];
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
        "rounded-xl border-2 p-3 text-left transition-all active:scale-[0.98]",
        "min-h-[104px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        PHASE_STYLES[slice.phase],
        slice.selected && multiMode && "ring-2 ring-primary ring-offset-2 ring-offset-background",
        focusFrameId === slice.frameId && "ring-2 ring-amber-400 ring-offset-2 animate-pulse",
        !slice.warm && slice.phase === "idle" && "opacity-90",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex min-w-0 items-center gap-1.5">
          <span
            className="flex h-5 w-5 shrink-0 items-center justify-center rounded-md bg-secondary text-[10px] font-bold text-secondary-foreground"
            aria-label={`Keyboard shortcut ${index + 1}`}
          >
            {index + 1}
          </span>
          <span className="truncate text-xs font-semibold uppercase tracking-wide text-primary">
            {slice.shortLabel}
          </span>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1">
          <Badge variant={phaseBadge.variant} className="h-5 px-1.5 text-[10px] capitalize">
            {phaseBadge.label}
          </Badge>
          <span
            className={cn(
              "h-2 w-2 rounded-full",
              slice.warm ? "bg-emerald-400" : "bg-muted-foreground/40",
            )}
            title={slice.warm ? "Warm" : "Cold"}
            aria-hidden
          />
        </div>
      </div>
      <p className="mt-2 line-clamp-2 text-sm font-medium leading-snug">{slice.label}</p>
      <p className="mt-1.5 text-xs text-muted-foreground">
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