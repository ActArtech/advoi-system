/**
 * User-defined preset chains (localStorage). Python mirror in tests/test_agent_slices.py.
 */

import { presetById } from "./slicePresets";
import type { SlicePreset } from "./slicePresets";

export type UserPresetChain = {
  id: string;
  label: string;
  presetIds: string[];
  dispatchAfter?: boolean;
  source: "user";
};

const STORAGE_KEY = "advoi:user-slice-chains";
export const MAX_USER_CHAINS = 6;

function canUseStorage(): boolean {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

function slugifyId(label: string): string {
  const base = label
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_|_$/g, "")
    .slice(0, 32);
  return base ? `uchain_${base}` : `uchain_${Date.now()}`;
}

export function readUserChains(): UserPresetChain[] {
  if (!canUseStorage()) return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed
      .filter((c): c is UserPresetChain => Boolean(c && typeof c === "object" && "presetIds" in c))
      .map((c) => ({ ...c, source: "user" as const }));
  } catch {
    return [];
  }
}

export function saveUserChain(input: {
  label: string;
  presetIds: string[];
  dispatchAfter?: boolean;
  id?: string;
}): UserPresetChain[] {
  const presetIds = input.presetIds.filter(Boolean);
  if (presetIds.length < 2) return readUserChains();
  const existing = readUserChains();
  const chain: UserPresetChain = {
    id: input.id ?? slugifyId(input.label),
    label: input.label.slice(0, 40),
    presetIds: [...presetIds],
    dispatchAfter: input.dispatchAfter,
    source: "user",
  };
  const withoutDup = existing.filter((c) => c.id !== chain.id);
  const next = [chain, ...withoutDup].slice(0, MAX_USER_CHAINS);
  if (canUseStorage()) {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    } catch {
      // ignore quota
    }
  }
  return next;
}

export function deleteUserChain(id: string): UserPresetChain[] {
  const next = readUserChains().filter((c) => c.id !== id);
  if (canUseStorage()) {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    } catch {
      // ignore
    }
  }
  return next;
}

export function exportUserChainsJson(chains?: UserPresetChain[]): string {
  const data = chains ?? readUserChains();
  return JSON.stringify({ version: 1, exportedAt: Date.now(), chains: data }, null, 2);
}

export function importUserChainsJson(json: string): UserPresetChain[] {
  const parsed = JSON.parse(json) as unknown;
  if (!parsed || typeof parsed !== "object") return readUserChains();
  const raw = (parsed as { chains?: unknown }).chains;
  if (!Array.isArray(raw)) return readUserChains();
  const imported: UserPresetChain[] = raw
    .filter((c): c is UserPresetChain => Boolean(c && typeof c === "object" && "presetIds" in c))
    .map((c) => ({ ...c, source: "user" as const }))
    .slice(0, MAX_USER_CHAINS);
  if (canUseStorage()) {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(imported));
    } catch {
      // ignore
    }
  }
  return imported;
}

/** Resolve builtin + user preset ids into runnable presets. */
export function resolveUserChainPresets(
  chain: Pick<UserPresetChain, "presetIds">,
  userPresets: readonly SlicePreset[] = [],
): SlicePreset[] {
  const userById = new Map(userPresets.map((p) => [p.id, p]));
  return chain.presetIds
    .map((id) => presetById(id) ?? userById.get(id))
    .filter((p): p is SlicePreset => p != null);
}

export function chainDraftLabel(presetIds: readonly string[], presets: readonly SlicePreset[]): string {
  const byId = new Map(presets.map((p) => [p.id, p.label]));
  return presetIds.map((id) => byId.get(id) ?? id).join(" → ");
}