"use client";

import { Badge } from "@/components/ui/badge";
import { PwaHomeOnboarding } from "@/components/PwaHomeOnboarding";
import { VoiceSession } from "@/components/VoiceSession";

export function VoicePane() {
  return (
    <div className="space-y-4 pb-4">
      <header className="space-y-2 pt-2">
        <Badge>Stage 2 · Mobile shell</Badge>
        <h1 className="text-2xl font-semibold tracking-tight">ADVoi</h1>
        <p className="text-sm text-muted-foreground">
          Portfolio voice layer. Thin wrapper over Hermes, fleet, and memory.
        </p>
      </header>
      <PwaHomeOnboarding />
      <VoiceSession />
    </div>
  );
}