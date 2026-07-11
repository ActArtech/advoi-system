import type { ProjectsCatalog } from "./projectModel";

export async function fetchProjectsCatalog(apiBase: string): Promise<ProjectsCatalog> {
  const resp = await fetch(`${apiBase}/portfolio/projects`);
  if (!resp.ok) {
    throw new Error(`Failed to load projects (${resp.status})`);
  }
  return (await resp.json()) as ProjectsCatalog;
}

export async function activateProjectOnServer(
  apiBase: string,
  ventureId: string,
  functionId?: string | null,
): Promise<{ ok?: boolean; venture_id?: string; venture_name?: string; frame_id?: string | null }> {
  const resp = await fetch(`${apiBase}/portfolio/active`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      venture_id: ventureId,
      function_id: functionId ?? null,
    }),
  });
  if (!resp.ok) {
    throw new Error(`Failed to activate project (${resp.status})`);
  }
  return (await resp.json()) as {
    ok?: boolean;
    venture_id?: string;
    venture_name?: string;
    frame_id?: string | null;
  };
}