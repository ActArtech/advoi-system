"use client";

import { Badge } from "@/components/ui/badge";
import { SLICE_PRESETS } from "@/lib/agents/slicePresets";
import type { SlicePreset } from "@/lib/agents/slicePresets";
import { cn } from "@/lib/utils";

type SlicePresetsBarProps = {
  onSelect: (preset: SlicePreset) => void;
  disabled?: boolean;
};

export function SlicePresetsBar({ onSelect, disabled }: SlicePresetsBarProps) {
  return (
    <div
      className="flex flex-wrap gap-1.5"
      role="group"
      aria-label="Slice presets"
      data-testid="slice-presets-bar"
    >
      {SLICE_PRESETS.map((preset) => (
        <button
          key={preset.id}
          type="button"
          disabled={disabled}
          onClick={() => onSelect(preset)}
          data-testid={`slice-preset-${preset.id}`}
          className={cn(
            "rounded-full border-0 bg-transparent p-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
            disabled && "pointer-events-none opacity-50",
          )}
        >
          <Badge
            variant="outline"
            className="cursor-pointer text-[10px] font-normal transition-colors hover:bg-secondary/80"
          >
            {preset.label}
          </Badge>
        </button>
      ))}
    </div>
  );
}