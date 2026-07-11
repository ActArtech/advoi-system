"use client";

import { Badge } from "@/components/ui/badge";
import { describeWavePlan } from "@/lib/agents/agentSlices";
import type { RunExecutionMode } from "@/lib/agents/types";

type SliceWavePreviewProps = {
  frameIds: string[];
  mode: RunExecutionMode;
};

export function SliceWavePreview({ frameIds, mode }: SliceWavePreviewProps) {
  if (frameIds.length === 0) return null;

  const plan = describeWavePlan(frameIds, mode);

  return (
    <div
      className="flex flex-wrap gap-1.5"
      data-testid="slice-wave-preview"
      aria-label="Wave plan preview"
    >
      {plan.waves.map((wave) => (
        <Badge key={wave.index} variant="outline" className="text-[10px] font-normal">
          {plan.waveCount > 1 ? `Wave ${wave.index + 1}` : "Parallel"}:{" "}
          {wave.labels.join(" · ")}
        </Badge>
      ))}
    </div>
  );
}