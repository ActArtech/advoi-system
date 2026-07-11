"use client";

import { Badge } from "@/components/ui/badge";
import { AgentsOrchestrator } from "@/components/agents/AgentsOrchestrator";

export function AgentsPane() {
  return (
    <div className="space-y-4 pb-4">
      <header className="space-y-1 pt-2">
        <Badge>Parallel orchestration</Badge>
        <h2 className="text-xl font-semibold tracking-tight">Agents</h2>
        <p className="text-sm text-muted-foreground">
          Six specialist slices — run one, select many, or fire all in parallel.
        </p>
      </header>
      <AgentsOrchestrator />
    </div>
  );
}