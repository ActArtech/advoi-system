"use client";

import { Badge } from "@/components/ui/badge";
import { PwaHomeBriefsSurface } from "@/components/PwaHomeBriefsSurface";

export function BriefsPane() {
  return (
    <div className="space-y-4 pb-4">
      <header className="space-y-1 pt-2">
        <Badge variant="secondary">Decision queue</Badge>
        <h2 className="text-xl font-semibold tracking-tight">Briefs</h2>
        <p className="text-sm text-muted-foreground">
          Open briefs and review queue from Postgres.
        </p>
      </header>
      <PwaHomeBriefsSurface />
    </div>
  );
}