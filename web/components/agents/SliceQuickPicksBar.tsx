"use client";

import { SLICE_QUICK_PICKS } from "@/lib/agents/sliceQuickPicks";
import styles from "./agentsTheme.module.css";

type SliceQuickPicksBarProps = {
  disabled?: boolean;
  onPick: (pickId: string) => void;
};

export function SliceQuickPicksBar({ disabled, onPick }: SliceQuickPicksBarProps) {
  return (
    <div
      className={styles.quickPickRow}
      role="group"
      aria-label="Quick selection picks"
      data-testid="slice-quick-picks"
    >
      <span className={styles.sectionLabel}>Quick pick</span>
      {SLICE_QUICK_PICKS.map((pick) => (
        <button
          key={pick.id}
          type="button"
          disabled={disabled}
          onClick={() => onPick(pick.id)}
          data-testid={`slice-quick-pick-${pick.id}`}
          className={pick.action === "clear" ? styles.quickPickClear : styles.quickPickPill}
        >
          {pick.label}
        </button>
      ))}
    </div>
  );
}