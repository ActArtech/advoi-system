"use client";

import { Badge } from "@/components/ui/badge";
import { AgentsOrchestrator } from "@/components/agents/AgentsOrchestrator";

export function AgentsPane() {
  return (
    <div className="space-y-4 pb-6" data-testid="agents-pane">
      <header className="space-y-2 rounded-xl border border-primary/20 bg-primary/5 p-4 pt-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge className="bg-primary text-primary-foreground">Multi-agent v2</Badge>
          <Badge variant="outline">Queue · Chains · Squads</Badge>
        </div>
        <h2 className="text-xl font-semibold tracking-tight">Agent orchestrator</h2>
        <p className="text-sm leading-relaxed text-muted-foreground">
          Tap a slice to run (keys 1-6). Use presets, chains, and squads for multi-wave runs.
          Queue batches while busy. History and Export all live below the grid.
        </p>
      </header>
      <AgentsOrchestrator />
    </div>
  );
}