/**
 * Project selector model — keep Python mirror in tests/test_project_selector.py in sync.
 */

export type ProjectFunctionKind = "frame" | "bet" | "custom";

export type ProjectFunction = {
  id: string;
  label: string;
  kind: ProjectFunctionKind;
  frame_id?: string;
  status?: string;
};

export type VentureProject = {
  id: string;
  name: string;
  status: string;
  fleet_slug?: string | null;
  squads: string[];
  functions: ProjectFunction[];
};

export type ProjectsCatalog = {
  ventures: VentureProject[];
  active_venture_id?: string | null;
  active_fleet_slug?: string | null;
  gate_active_slug?: string | null;
  source?: string | null;
};

export const PROJECT_SWITCH_EVENT = "advoi:project-switch";

export type ProjectSwitchDetail = {
  ventureId: string;
  ventureName?: string;
  functionId?: string;
  frameId?: string;
  source?: string;
};

export type UserProjectFeature = {
  id: string;
  ventureId: string;
  label: string;
  note?: string;
};

export function mergeUserFeatures(
  venture: VentureProject,
  userFeatures: readonly UserProjectFeature[],
): ProjectFunction[] {
  const custom = userFeatures
    .filter((row) => row.ventureId === venture.id)
    .map((row) => ({
      id: row.id,
      label: row.label,
      kind: "custom" as const,
    }));
  return [...venture.functions, ...custom];
}

export function ventureById(
  catalog: ProjectsCatalog | null | undefined,
  ventureId: string | null | undefined,
): VentureProject | null {
  if (!catalog || !ventureId) return null;
  return catalog.ventures.find((row) => row.id === ventureId) ?? null;
}

export function filterSquadsForVenture<T extends { id: string; venture_id?: string }>(
  squads: readonly T[],
  ventureId: string | null | undefined,
): T[] {
  if (!ventureId) return [...squads];
  const scoped = squads.filter((row) => row.venture_id === ventureId);
  return scoped.length > 0 ? scoped : [...squads];
}

export function projectSelectorLabel(
  venture: VentureProject | null,
  functionId?: string | null,
): string {
  if (!venture) return "Select project";
  if (!functionId) return venture.name;
  const fn = venture.functions.find((row) => row.id === functionId);
  return fn ? `${venture.name} · ${fn.label}` : venture.name;
}

export function makeUserFeatureId(label: string): string {
  const slug = label
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
  return `custom-${slug || "feature"}-${Date.now().toString(36)}`;
}