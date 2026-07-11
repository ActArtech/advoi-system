"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { activateProjectOnServer, fetchProjectsCatalog } from "@/lib/portfolio/projectCatalog";
import {
  appendUserProjectFeature,
  readActiveFunctionId,
  readActiveVentureId,
  readUserProjectFeatures,
  saveActiveFunctionId,
  saveActiveVentureId,
} from "@/lib/portfolio/projectPreferences";
import {
  makeUserFeatureId,
  mergeUserFeatures,
  PROJECT_SWITCH_EVENT,
  projectSelectorLabel,
  ventureById,
  type ProjectSwitchDetail,
  type ProjectsCatalog,
  type UserProjectFeature,
  type VentureProject,
} from "@/lib/portfolio/projectModel";
import { RUN_FRAME_EVENT } from "@/components/pwaOnboarding";

type ProjectContextValue = {
  catalog: ProjectsCatalog | null;
  loading: boolean;
  error: string | null;
  activeVentureId: string | null;
  activeFunctionId: string | null;
  activeVenture: VentureProject | null;
  userFeatures: UserProjectFeature[];
  selectorLabel: string;
  refreshCatalog: () => Promise<void>;
  selectProject: (
    ventureId: string,
    options?: { functionId?: string | null; source?: string; runFrame?: boolean },
  ) => Promise<void>;
  addFeature: (ventureId: string, label: string) => void;
};

const ProjectContext = createContext<ProjectContextValue | null>(null);

function apiBaseFromEnv(): string {
  return process.env.NEXT_PUBLIC_API_BASE ?? "/api";
}

export function ProjectProvider({ children }: { children: ReactNode }) {
  const apiBase = apiBaseFromEnv();
  const [catalog, setCatalog] = useState<ProjectsCatalog | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeVentureId, setActiveVentureId] = useState<string | null>(null);
  const [activeFunctionId, setActiveFunctionId] = useState<string | null>(null);
  const [userFeatures, setUserFeatures] = useState<UserProjectFeature[]>([]);

  const refreshCatalog = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const next = await fetchProjectsCatalog(apiBase);
      setCatalog(next);
      const storedVenture = readActiveVentureId();
      const storedFunction = readActiveFunctionId();
      const resolvedVenture =
        storedVenture && next.ventures.some((row) => row.id === storedVenture)
          ? storedVenture
          : next.active_venture_id ?? next.ventures[0]?.id ?? null;
      setActiveVentureId(resolvedVenture);
      setActiveFunctionId(storedFunction);
      if (resolvedVenture && resolvedVenture !== storedVenture) {
        saveActiveVentureId(resolvedVenture);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load projects");
    } finally {
      setLoading(false);
    }
  }, [apiBase]);

  useEffect(() => {
    setUserFeatures(readUserProjectFeatures());
    void refreshCatalog();
  }, [refreshCatalog]);

  const activeVenture = useMemo(() => {
    const base = ventureById(catalog, activeVentureId);
    if (!base) return null;
    return {
      ...base,
      functions: mergeUserFeatures(base, userFeatures),
    };
  }, [catalog, activeVentureId, userFeatures]);

  const selectorLabel = useMemo(
    () => projectSelectorLabel(activeVenture, activeFunctionId),
    [activeVenture, activeFunctionId],
  );

  const selectProject = useCallback(
    async (
      ventureId: string,
      options?: { functionId?: string | null; source?: string; runFrame?: boolean },
    ) => {
      const venture = ventureById(catalog, ventureId);
      if (!venture) return;

      const functionId = options?.functionId ?? null;
      const fn = functionId
        ? mergeUserFeatures(venture, userFeatures).find((row) => row.id === functionId)
        : null;

      setActiveVentureId(ventureId);
      setActiveFunctionId(functionId);
      saveActiveVentureId(ventureId);
      saveActiveFunctionId(functionId);

      try {
        const activated = await activateProjectOnServer(apiBase, ventureId, functionId);
        const detail: ProjectSwitchDetail = {
          ventureId,
          ventureName: activated.venture_name ?? venture.name,
          functionId: functionId ?? undefined,
          frameId: fn?.frame_id ?? activated.frame_id ?? undefined,
          source: options?.source ?? "ui",
        };
        window.dispatchEvent(new CustomEvent(PROJECT_SWITCH_EVENT, { detail }));

        if (options?.runFrame !== false && detail.frameId) {
          window.dispatchEvent(
            new CustomEvent(RUN_FRAME_EVENT, {
              detail: { frameId: detail.frameId, refresh: true, source: "project_selector" },
            }),
          );
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to activate project");
      }
    },
    [apiBase, catalog, userFeatures],
  );

  const addFeature = useCallback((ventureId: string, label: string) => {
    const trimmed = label.trim();
    if (!trimmed) return;
    const feature: UserProjectFeature = {
      id: makeUserFeatureId(trimmed),
      ventureId,
      label: trimmed,
    };
    const rows = appendUserProjectFeature(feature);
    setUserFeatures(rows);
    void selectProject(ventureId, { functionId: feature.id, source: "add_feature" });
  }, [selectProject]);

  useEffect(() => {
    const onProjectSwitch = (ev: Event) => {
      const detail = (ev as CustomEvent<ProjectSwitchDetail>).detail;
      if (!detail?.ventureId) return;
      if (detail.ventureId === activeVentureId && detail.functionId === activeFunctionId) {
        return;
      }
      setActiveVentureId(detail.ventureId);
      setActiveFunctionId(detail.functionId ?? null);
      saveActiveVentureId(detail.ventureId);
      saveActiveFunctionId(detail.functionId ?? null);
    };
    window.addEventListener(PROJECT_SWITCH_EVENT, onProjectSwitch);
    return () => window.removeEventListener(PROJECT_SWITCH_EVENT, onProjectSwitch);
  }, [activeFunctionId, activeVentureId]);

  const value = useMemo(
    () => ({
      catalog,
      loading,
      error,
      activeVentureId,
      activeFunctionId,
      activeVenture,
      userFeatures,
      selectorLabel,
      refreshCatalog,
      selectProject,
      addFeature,
    }),
    [
      catalog,
      loading,
      error,
      activeVentureId,
      activeFunctionId,
      activeVenture,
      userFeatures,
      selectorLabel,
      refreshCatalog,
      selectProject,
      addFeature,
    ],
  );

  return <ProjectContext.Provider value={value}>{children}</ProjectContext.Provider>;
}

export function useProjectContext() {
  return useContext(ProjectContext);
}