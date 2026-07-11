/**
 * User-defined slice presets (localStorage). Python mirror in tests/test_agent_slices.py.
 */

import type { SlicePreset } from "./slicePresets";
import type { RunExecutionMode } from "./types";

export type UserSlicePreset = SlicePreset & { source: "user" };

const STORAGE_KEY = "advoi:user-slice-presets";
export const MAX_USER_PRESETS = 8;

function canUseStorage(): boolean {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

function slugifyId(label: string): string {
  const base = label
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_|_$/g, "")
    .slice(0, 32);
  return base ? `user_${base}` : `user_${Date.now()}`;
}

export function readUserPresets(): UserSlicePreset[] {
  if (!canUseStorage()) return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed
      .filter((p): p is UserSlicePreset => Boolean(p && typeof p === "object" && "id" in p))
      .map((p) => ({ ...p, source: "user" as const }));
  } catch {
    return [];
  }
}

export function saveUserPreset(input: {
  label: string;
  frameIds: string[];
  mode: RunExecutionMode;
  description?: string;
  id?: string;
}): UserSlicePreset[] {
  const existing = readUserPresets();
  const preset: UserSlicePreset = {
    id: input.id ?? slugifyId(input.label),
    label: input.label.slice(0, 40),
    description: input.description,
    frameIds: [...input.frameIds],
    mode: input.mode,
    source: "user",
  };
  const withoutDup = existing.filter((p) => p.id !== preset.id);
  const next = [preset, ...withoutDup].slice(0, MAX_USER_PRESETS);
  if (canUseStorage()) {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    } catch {
      // ignore quota
    }
  }
  return next;
}

export function deleteUserPreset(id: string): UserSlicePreset[] {
  const next = readUserPresets().filter((p) => p.id !== id);
  if (canUseStorage()) {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    } catch {
      // ignore
    }
  }
  return next;
}