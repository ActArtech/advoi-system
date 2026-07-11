"use client";

import { useLongPress } from "@/hooks/useLongPress";
import type { AgentSliceModel } from "@/lib/agents/types";
import { formatRelativeTimeFromValue } from "@/lib/agents/sliceRunLog";
import { cn } from "@/lib/utils";
import styles from "./agentsTheme.module.css";

const PHASE_TILE: Record<AgentSliceModel["phase"], string> = {
  idle: styles.sliceTileIdle,
  queued: styles.sliceTileQueued,
  running: styles.sliceTileRunning,
  ok: styles.sliceTileOk,
  error: styles.sliceTileError,
};

const PHASE_CHIP: Record<AgentSliceModel["phase"], string> = {
  idle: styles.phaseIdle,
  queued: styles.phaseQueued,
  running: styles.phaseRunning,
  ok: styles.phaseOk,
  error: styles.phaseError,
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
  const longPress = useLongPress(
    () => {
      if (!busy && onLongPressDispatch && slice.squadIds.length > 0) {
        onLongPressDispatch(slice);
      }
    },
    { disabled: busy || !onLongPressDispatch || slice.squadIds.length === 0 },
  );

  const meta =
    slice.phase === "running"
      ? "running..."
      : slice.phase === "queued"
        ? "queued..."
        : slice.phase === "idle" && slice.lastRunAt
          ? formatRelativeTimeFromValue(slice.lastRunAt)
          : slice.lastStatus
            ? slice.lastStatus
            : slice.warm
              ? "warm"
              : "tap run · hold dispatch";

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
        styles.sliceTile,
        PHASE_TILE[slice.phase],
        slice.selected && multiMode && styles.sliceTileSelected,
        focusFrameId === slice.frameId && styles.sliceTileFocus,
        !slice.warm && slice.phase === "idle" && "opacity-90",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex min-w-0 items-center gap-1.5">
          <span className={styles.sliceKey} aria-label={`Keyboard shortcut ${index + 1}`}>
            {index + 1}
          </span>
          <span className={styles.sliceShort}>{slice.shortLabel}</span>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1">
          <span className={cn(styles.phaseChip, PHASE_CHIP[slice.phase])}>{slice.phase}</span>
          <span
            className={cn(styles.warmDot, slice.warm ? styles.warmDotHot : styles.warmDotCold)}
            title={slice.warm ? "Warm" : "Cold"}
            aria-hidden
          />
        </div>
      </div>
      <p className={styles.sliceLabel}>{slice.label}</p>
      <p className={styles.sliceMeta}>{meta}</p>
      {slice.squadIds.length > 0 ? (
        <p className={cn(styles.sliceMeta, "mt-0.5 opacity-80")}>{slice.squadIds.join(", ")}</p>
      ) : null}
    </button>
  );
}