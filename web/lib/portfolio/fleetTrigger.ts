import { fleetActionTranscript } from "./projectModel";

export type FleetAction = "wake_firstmate" | "start_development" | "run_next_backlog" | "fleet_stop";

export const FLEET_ACTION_LABELS: Record<FleetAction, string> = {
  wake_firstmate: "Wake FirstMate",
  start_development: "Start dev",
  run_next_backlog: "Next backlog",
  fleet_stop: "Stop fleet",
};

export type FleetTriggerResult = {
  ok?: boolean;
  status?: string;
  spoken?: string;
  prompt?: string;
  action?: string;
  project?: string;
};

export async function triggerFleetAction(
  apiBase: string,
  action: FleetAction,
  options: { project?: string | null; confirmed?: boolean },
): Promise<FleetTriggerResult> {
  const project = options.project?.trim() || null;
  const confirmed = options.confirmed ?? false;
  const transcript = fleetActionTranscript(action, project, confirmed);

  const resp = await fetch(`${apiBase}/fleet/trigger`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      action,
      confirmed,
      project,
      transcript,
    }),
  });

  if (!resp.ok) {
    throw new Error(`Fleet trigger returned ${resp.status}`);
  }

  return (await resp.json()) as FleetTriggerResult;
}