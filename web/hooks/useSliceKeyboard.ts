"use client";

import { useEffect } from "react";
import type { AgentSliceModel } from "@/lib/agents/types";

type SliceKeyboardHandlers = {
  slices: AgentSliceModel[];
  busy: boolean;
  failedCount: number;
  selectedCount?: number;
  multiMode?: boolean;
  followUpCount?: number;
  queueDepth?: number;
  enabled?: boolean;
  onRunSlice: (slice: AgentSliceModel) => void;
  onRetryFailed: () => void;
  onCancel: () => void;
  onToggleMulti: () => void;
  onRunAll?: () => void;
  onRunSelected?: () => void;
  onRunSelectedStagger?: () => void;
  onRunPrimaryFollowUp?: () => void;
  onRunSecondaryFollowUp?: () => void;
  onStackSelected?: () => void;
  onRunQueue?: () => void;
  onOpenQueue?: () => void;
  onOpenHistory?: () => void;
  onSelectAll?: () => void;
};

function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true;
  return target.isContentEditable;
}

/**
 * Agents tab keyboard shortcuts:
 * 1-6 run slice, Enter run selected/all, Shift+Enter stagger,
 * C / Shift+C follow-up chips, S stack batch, Y run queue, Q queue, H history, A select all,
 * R retry, Escape cancel, M toggle multi-select.
 */
export function useSliceKeyboard({
  slices,
  busy,
  failedCount,
  selectedCount = 0,
  multiMode = false,
  followUpCount = 0,
  queueDepth = 0,
  enabled = true,
  onRunSlice,
  onRetryFailed,
  onCancel,
  onToggleMulti,
  onRunAll,
  onRunSelected,
  onRunSelectedStagger,
  onRunPrimaryFollowUp,
  onRunSecondaryFollowUp,
  onStackSelected,
  onRunQueue,
  onOpenQueue,
  onOpenHistory,
  onSelectAll,
}: SliceKeyboardHandlers) {
  useEffect(() => {
    if (!enabled) return;

    const onKeyDown = (ev: KeyboardEvent) => {
      if (isTypingTarget(ev.target)) return;

      if (ev.key === "Escape" && busy) {
        ev.preventDefault();
        onCancel();
        return;
      }

      if (busy) return;

      if (ev.key === "Enter") {
        if (ev.shiftKey && onRunSelectedStagger) {
          ev.preventDefault();
          onRunSelectedStagger();
          return;
        }
        if (selectedCount > 0 && onRunSelected) {
          ev.preventDefault();
          onRunSelected();
          return;
        }
        if (onRunAll) {
          ev.preventDefault();
          onRunAll();
        }
        return;
      }

      if ((ev.key === "c" || ev.key === "C") && followUpCount > 0) {
        if (ev.shiftKey && followUpCount > 1 && onRunSecondaryFollowUp) {
          ev.preventDefault();
          onRunSecondaryFollowUp();
          return;
        }
        if (onRunPrimaryFollowUp) {
          ev.preventDefault();
          onRunPrimaryFollowUp();
        }
        return;
      }

      if ((ev.key === "s" || ev.key === "S") && onStackSelected) {
        ev.preventDefault();
        onStackSelected();
        return;
      }

      if ((ev.key === "y" || ev.key === "Y") && queueDepth > 0 && onRunQueue) {
        ev.preventDefault();
        onRunQueue();
        return;
      }

      if ((ev.key === "q" || ev.key === "Q") && queueDepth > 0 && onOpenQueue) {
        ev.preventDefault();
        onOpenQueue();
        return;
      }

      if ((ev.key === "h" || ev.key === "H") && onOpenHistory) {
        ev.preventDefault();
        onOpenHistory();
        return;
      }

      if ((ev.key === "a" || ev.key === "A") && onSelectAll) {
        ev.preventDefault();
        onSelectAll();
        return;
      }

      const digit = ev.key;
      if (digit >= "1" && digit <= "6" && !ev.shiftKey && !ev.ctrlKey && !ev.altKey) {
        const idx = Number(digit) - 1;
        const slice = slices[idx];
        if (slice) {
          ev.preventDefault();
          onRunSlice(slice);
        }
        return;
      }

      if ((ev.key === "r" || ev.key === "R") && failedCount > 0) {
        ev.preventDefault();
        onRetryFailed();
        return;
      }

      if (ev.key === "m" || ev.key === "M") {
        ev.preventDefault();
        onToggleMulti();
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [
    slices,
    busy,
    failedCount,
    selectedCount,
    multiMode,
    followUpCount,
    queueDepth,
    enabled,
    onRunSlice,
    onRetryFailed,
    onCancel,
    onToggleMulti,
    onRunAll,
    onRunSelected,
    onRunSelectedStagger,
    onRunPrimaryFollowUp,
    onRunSecondaryFollowUp,
    onStackSelected,
    onRunQueue,
    onOpenQueue,
    onOpenHistory,
    onSelectAll,
  ]);
}