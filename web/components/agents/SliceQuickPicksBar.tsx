"use client";

import { SLICE_QUICK_PICKS } from "@/lib/agents/sliceQuickPicks";
import { ListPlus, Play } from "lucide-react";
import styles from "./agentsTheme.module.css";

type SliceQuickPicksBarProps = {
  disabled?: boolean;
  onPick: (pickId: string) => void;
  onRunPick?: (pickId: string) => void;
  onStackPick?: (pickId: string) => void;
};

export function SliceQuickPicksBar({
  disabled,
  onPick,
  onRunPick,
  onStackPick,
}: SliceQuickPicksBarProps) {
  return (
    <div
      className={styles.quickPickRow}
      role="group"
      aria-label="Quick selection picks"
      data-testid="slice-quick-picks"
    >
      <span className={styles.sectionLabel}>Quick pick</span>
      {SLICE_QUICK_PICKS.map((pick) => {
        const canRun = pick.action !== "clear" && onRunPick;
        const canStack = pick.action !== "clear" && onStackPick;
        return (
          <span key={pick.id} className={styles.quickPickGroup}>
            <button
              type="button"
              disabled={disabled}
              onClick={() => onPick(pick.id)}
              data-testid={`slice-quick-pick-${pick.id}`}
              className={pick.action === "clear" ? styles.quickPickClear : styles.quickPickPill}
            >
              {pick.label}
            </button>
            {canRun ? (
              <button
                type="button"
                disabled={disabled}
                aria-label={`Run ${pick.label}`}
                onClick={() => onRunPick(pick.id)}
                data-testid={`slice-quick-run-${pick.id}`}
                className={styles.quickPickAction}
              >
                <Play className="h-3 w-3" />
              </button>
            ) : null}
            {canStack ? (
              <button
                type="button"
                disabled={disabled}
                aria-label={`Stack ${pick.label} in queue`}
                onClick={() => onStackPick(pick.id)}
                data-testid={`slice-quick-stack-${pick.id}`}
                className={styles.quickPickAction}
              >
                <ListPlus className="h-3 w-3" />
              </button>
            ) : null}
          </span>
        );
      })}
    </div>
  );
}