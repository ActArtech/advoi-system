/**
 * Persisted Agents tab orchestration preferences.
 */

import type { RunExecutionMode } from "./types";

const RUN_MODE_KEY = "advoi:slice-run-mode";
const AUTO_RUN_QUEUE_KEY = "advoi:slice-auto-run-queue";

function canUseStorage(): boolean {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

const VALID_MODES: RunExecutionMode[] = ["parallel", "wave", "stagger"];

export function readPreferredRunMode(): RunExecutionMode | null {
  if (!canUseStorage()) return null;
  try {
    const raw = window.localStorage.getItem(RUN_MODE_KEY);
    if (raw && VALID_MODES.includes(raw as RunExecutionMode)) {
      return raw as RunExecutionMode;
    }
  } catch {
    // ignore
  }
  return null;
}

export function savePreferredRunMode(mode: RunExecutionMode): void {
  if (!canUseStorage()) return;
  try {
    window.localStorage.setItem(RUN_MODE_KEY, mode);
  } catch {
    // ignore
  }
}

export function readAutoRunQueue(): boolean {
  if (!canUseStorage()) return false;
  try {
    return window.localStorage.getItem(AUTO_RUN_QUEUE_KEY) === "1";
  } catch {
    return false;
  }
}

export function saveAutoRunQueue(enabled: boolean): void {
  if (!canUseStorage()) return;
  try {
    window.localStorage.setItem(AUTO_RUN_QUEUE_KEY, enabled ? "1" : "0");
  } catch {
    // ignore
  }
}