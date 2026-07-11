"use client";

import { Button } from "@/components/ui/button";
import type { SliceFollowUp } from "@/lib/agents/slicePostRunSuggestions";
import { ListPlus, Play } from "lucide-react";
import styles from "./agentsTheme.module.css";

type SliceFollowUpBannerProps = {
  title: string;
  followUps: SliceFollowUp[];
  disabled?: boolean;
  onExecute: (followUp: SliceFollowUp) => void;
  onDismiss: () => void;
  hint?: string;
  testId?: string;
};

export function SliceFollowUpBanner({
  title,
  followUps,
  disabled,
  onExecute,
  onDismiss,
  hint,
  testId = "slice-follow-up-banner",
}: SliceFollowUpBannerProps) {
  if (followUps.length === 0) return null;

  return (
    <div className={styles.suggestion} data-testid={testId}>
      <p className={styles.suggestionText}>{title}</p>
      <div className={styles.suggestionChips}>
        {followUps.map((followUp, index) => {
          const isStack = followUp.action.kind === "stack_chain";
          const isPrimary = index === 0 && !isStack;
          return (
            <button
              key={followUp.id}
              type="button"
              disabled={disabled}
              onClick={() => onExecute(followUp)}
              data-testid={`follow-up-${followUp.id}`}
              className={isPrimary ? styles.ctaPrimary : styles.ctaOutline}
            >
              {isStack ? <ListPlus className="h-4 w-4" /> : <Play className="h-4 w-4" />}
              {followUp.label}
            </button>
          );
        })}
        <Button size="sm" variant="ghost" onClick={onDismiss} data-testid="dismiss-follow-ups">
          Dismiss
        </Button>
      </div>
      {hint ? <p className={styles.suggestionHint}>{hint}</p> : null}
    </div>
  );
}