"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ChevronDown, FolderKanban, Mic, Plus, Rocket } from "lucide-react";
import { useProjectContext } from "@/components/shell/ProjectContext";
import styles from "@/components/shell/projectSelector.module.css";
import {
  FLEET_ACTION_LABELS,
  triggerFleetAction,
  type FleetAction,
} from "@/lib/portfolio/fleetTrigger";
import { mergeUserFeatures } from "@/lib/portfolio/projectModel";

const FLEET_DROPDOWN_ACTIONS: FleetAction[] = [
  "wake_firstmate",
  "start_development",
  "run_next_backlog",
  "fleet_stop",
];

function apiBaseFromEnv(): string {
  return process.env.NEXT_PUBLIC_API_BASE ?? "/api";
}

export function ProjectSelector() {
  const ctx = useProjectContext();
  const apiBase = apiBaseFromEnv();
  const [open, setOpen] = useState(false);
  const [draftFeature, setDraftFeature] = useState("");
  const [fleetBusy, setFleetBusy] = useState(false);
  const [pendingFleet, setPendingFleet] = useState<FleetAction | null>(null);
  const [fleetMessage, setFleetMessage] = useState<string | null>(null);
  const panelRef = useRef<HTMLDivElement | null>(null);

  const ventures = ctx?.catalog?.ventures ?? [];
  const activeVentureId = ctx?.activeVentureId ?? null;
  const activeFunctionId = ctx?.activeFunctionId ?? null;
  const userFeatures = ctx?.userFeatures ?? [];
  const activeFleetSlug = ctx?.activeVenture?.fleet_slug?.trim() || null;

  const activeFunctions = useMemo(() => {
    const venture = ventures.find((row) => row.id === activeVentureId);
    if (!venture) return [];
    return mergeUserFeatures(venture, userFeatures);
  }, [activeVentureId, userFeatures, ventures]);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (ev: MouseEvent) => {
      const target = ev.target as Node | null;
      if (panelRef.current && target && !panelRef.current.contains(target)) {
        setOpen(false);
      }
    };
    window.addEventListener("mousedown", onPointerDown);
    return () => window.removeEventListener("mousedown", onPointerDown);
  }, [open]);

  const runFleetAction = useCallback(
    async (action: FleetAction) => {
      if (fleetBusy || !activeFleetSlug) return;
      const confirming = pendingFleet === action;
      setFleetBusy(true);
      setFleetMessage(null);
      try {
        const data = await triggerFleetAction(apiBase, action, {
          project: activeFleetSlug,
          confirmed: confirming,
        });
        if (data.status === "confirmation_required") {
          setPendingFleet(action);
          setFleetMessage(
            typeof data.prompt === "string"
              ? data.prompt
              : `Confirm ${FLEET_ACTION_LABELS[action].toLowerCase()} on ${activeFleetSlug}.`,
          );
          return;
        }
        setPendingFleet(null);
        const spoken =
          typeof data.spoken === "string"
            ? data.spoken
            : `${FLEET_ACTION_LABELS[action]} completed on ${activeFleetSlug}.`;
        setFleetMessage(spoken);
      } catch (err) {
        setPendingFleet(null);
        setFleetMessage(err instanceof Error ? err.message : "Fleet action failed.");
      } finally {
        setFleetBusy(false);
      }
    },
    [activeFleetSlug, apiBase, fleetBusy, pendingFleet],
  );

  if (!ctx) return null;

  return (
    <div className={styles.bar} ref={panelRef} data-testid="project-selector">
      <div className={styles.inner}>
        <button
          type="button"
          className={styles.trigger}
          aria-expanded={open}
          aria-haspopup="listbox"
          data-testid="project-selector-trigger"
          onClick={() => setOpen((value) => !value)}
        >
          <span className={styles.triggerMeta}>
            <span className={styles.triggerLabel}>
              <FolderKanban
                aria-hidden
                style={{ display: "inline", width: 14, height: 14, marginRight: 6, verticalAlign: -2 }}
              />
              {ctx.loading ? "Loading projects..." : ctx.selectorLabel}
            </span>
            <span className={styles.triggerHint}>
              {ctx.error ? ctx.error : "UI, voice, or function scope"}
            </span>
          </span>
          <ChevronDown aria-hidden size={16} />
        </button>
        <span className={styles.voiceHint}>
          <Mic aria-hidden size={12} style={{ display: "inline", marginRight: 4, verticalAlign: -1 }} />
          Say switch to project
        </span>
      </div>

      {open ? (
        <div className={styles.panel} role="listbox" data-testid="project-selector-panel">
          <div className={styles.panelHeader}>Portfolio projects</div>
          {ventures.map((venture) => {
            const functions = mergeUserFeatures(venture, userFeatures);
            const isActive = venture.id === activeVentureId;
            return (
              <div key={venture.id} className={styles.projectRow}>
                <button
                  type="button"
                  className={styles.projectButton}
                  data-active={isActive}
                  data-testid={`project-option-${venture.id}`}
                  onClick={() => {
                    void ctx.selectProject(venture.id, { source: "dropdown" });
                    setPendingFleet(null);
                    setFleetMessage(null);
                    setOpen(false);
                  }}
                >
                  <span>
                    <div className={styles.projectName}>{venture.name}</div>
                    <div className={styles.projectSlug}>{venture.id}</div>
                  </span>
                  {isActive ? <span aria-hidden>Active</span> : null}
                </button>
                {isActive && functions.length > 0 ? (
                  <div className={styles.functions}>
                    {functions.map((fn) => (
                      <button
                        key={fn.id}
                        type="button"
                        className={styles.functionChip}
                        data-active={fn.id === activeFunctionId}
                        data-testid={`project-function-${fn.id}`}
                        onClick={() => {
                          void ctx.selectProject(venture.id, {
                            functionId: fn.id,
                            source: "function_chip",
                            runFrame: fn.kind === "frame",
                          });
                          setOpen(false);
                        }}
                      >
                        {fn.label}
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>
            );
          })}

          {activeVentureId && activeFleetSlug ? (
            <div className={styles.fleetSection} data-testid="project-fleet-actions">
              <div className={styles.panelHeader}>
                <Rocket
                  aria-hidden
                  size={12}
                  style={{ display: "inline", marginRight: 5, verticalAlign: -1 }}
                />
                FirstMate on {activeFleetSlug}
              </div>
              <div className={styles.fleetActions}>
                {FLEET_DROPDOWN_ACTIONS.map((action) => {
                  const isPending = pendingFleet === action;
                  const label = isPending ? "Confirm" : FLEET_ACTION_LABELS[action];
                  return (
                    <button
                      key={action}
                      type="button"
                      className={`${styles.fleetBtn} ${action === "fleet_stop" ? styles.fleetBtnDanger : ""}`}
                      data-pending={isPending}
                      data-testid={`project-fleet-${action}`}
                      disabled={fleetBusy}
                      onClick={() => void runFleetAction(action)}
                    >
                      {label}
                    </button>
                  );
                })}
              </div>
              {fleetMessage ? (
                <p
                  className={`${styles.fleetHint} ${
                    pendingFleet ? styles.fleetHintWarn : styles.fleetHintOk
                  }`}
                  data-testid="project-fleet-message"
                >
                  {fleetMessage}
                </p>
              ) : (
                <p className={styles.fleetHint}>
                  Tap Wake FirstMate, then Confirm. Targets fleet slug {activeFleetSlug}.
                </p>
              )}
            </div>
          ) : null}

          {activeVentureId ? (
            <div className={styles.addRow}>
              <input
                className={styles.addInput}
                placeholder="Add feature or function label"
                value={draftFeature}
                data-testid="project-add-feature-input"
                onChange={(ev) => setDraftFeature(ev.target.value)}
                onKeyDown={(ev) => {
                  if (ev.key === "Enter" && draftFeature.trim()) {
                    ctx.addFeature(activeVentureId, draftFeature);
                    setDraftFeature("");
                  }
                }}
              />
              <button
                type="button"
                className={styles.addButton}
                data-testid="project-add-feature-button"
                onClick={() => {
                  if (!draftFeature.trim()) return;
                  ctx.addFeature(activeVentureId, draftFeature);
                  setDraftFeature("");
                }}
              >
                <Plus aria-hidden size={12} style={{ display: "inline", marginRight: 4, verticalAlign: -1 }} />
                Add
              </button>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}