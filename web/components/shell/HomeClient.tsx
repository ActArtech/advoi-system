"use client";

import { AppShell } from "@/components/shell/AppShell";
import { VoicePane } from "@/components/shell/VoicePane";
import { AgentsPane } from "@/components/shell/AgentsPane";
import { BriefsPane } from "@/components/shell/BriefsPane";
import { MorePane } from "@/components/shell/MorePane";

export function HomeClient() {
  return (
    <AppShell
      voicePane={<VoicePane />}
      agentsPane={<AgentsPane />}
      briefsPane={<BriefsPane />}
      morePane={<MorePane />}
    />
  );
}