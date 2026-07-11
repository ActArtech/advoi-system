/**
 * Session-scoped history of slice orchestration runs.
 */

import type { RunExecutionMode } from "./types";

export type SliceRunLogEntry = {
  id: string;
  ts: number;
  label: string;
  mode: RunExecutionMode;
  frameCount: number;
  okCount: number;
  failCount: number;
  summary?: string;
  /** Stored for one-tap re-run from history drawer */
  frameIds?: string[];
};

const STORAGE_KEY = "advoi:slice-run-log";
const MAX_ENTRIES = 20;

function canUseSessionStorage(): boolean {
  return typeof window !== "undefined" && typeof window.sessionStorage !== "undefined";
}

function newEntryId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `run-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

export function readSliceRunLog(): SliceRunLogEntry[] {
  if (!canUseSessionStorage()) return [];
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed as SliceRunLogEntry[];
  } catch {
    return [];
  }
}

export function appendSliceRunLog(
  entry: Omit<SliceRunLogEntry, "id" | "ts"> & Partial<Pick<SliceRunLogEntry, "id" | "ts">>,
): SliceRunLogEntry[] {
  const full: SliceRunLogEntry = {
    id: entry.id ?? newEntryId(),
    ts: entry.ts ?? Date.now(),
    label: entry.label,
    mode: entry.mode,
    frameCount: entry.frameCount,
    okCount: entry.okCount,
    failCount: entry.failCount,
    summary: entry.summary,
  };
  const next = [full, ...readSliceRunLog()].slice(0, MAX_ENTRIES);
  if (canUseSessionStorage()) {
    try {
      window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    } catch {
      // ignore quota / private-mode errors
    }
  }
  return next;
}

export function formatRelativeTime(ts: number): string {
  const diffSec = Math.round((Date.now() - ts) / 1000);
  const rtf = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });
  if (Math.abs(diffSec) < 60) return rtf.format(-diffSec, "second");
  const diffMin = Math.round(diffSec / 60);
  if (Math.abs(diffMin) < 60) return rtf.format(-diffMin, "minute");
  const diffHr = Math.round(diffMin / 60);
  if (Math.abs(diffHr) < 24) return rtf.format(-diffHr, "hour");
  const diffDay = Math.round(diffHr / 24);
  return rtf.format(-diffDay, "day");
}

export function formatRelativeTimeFromValue(value: string): string {
  const ms = Number(value);
  if (Number.isFinite(ms) && ms > 0) return formatRelativeTime(ms);
  const parsed = Date.parse(value);
  if (!Number.isNaN(parsed)) return formatRelativeTime(parsed);
  return value;
}

export function clearSliceRunLog(): void {
  if (!canUseSessionStorage()) return;
  try {
    window.sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    // ignore
  }
}