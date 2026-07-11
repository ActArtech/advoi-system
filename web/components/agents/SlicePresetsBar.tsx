"use client";

import { BookmarkPlus } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { allPresetsForBar } from "@/lib/agents/slicePresets";
import type { SlicePreset } from "@/lib/agents/slicePresets";
import type { UserSlicePreset } from "@/lib/agents/customUserPresets";
import { cn } from "@/lib/utils";

type SlicePresetsBarProps = {
  onSelect: (preset: SlicePreset) => void;
  userPresets?: UserSlicePreset[];
  onSavePreset?: () => void;
  canSavePreset?: boolean;
  chainButtons?: { id: string; label: string; onRun: () => void }[];
  disabled?: boolean;
};

export function SlicePresetsBar({
  onSelect,
  userPresets = [],
  onSavePreset,
  canSavePreset,
  chainButtons = [],
  disabled,
}: SlicePresetsBarProps) {
  const allPresets = allPresetsForBar(userPresets);

  return (
    <div className="space-y-2">
      <div
        className="flex flex-wrap gap-1.5"
        role="group"
        aria-label="Slice presets"
        data-testid="slice-presets-bar"
      >
        {allPresets.map((preset) => {
          const isUser = "source" in preset && preset.source === "user";
          const testId = isUser
            ? `slice-preset-user-${preset.id}`
            : `slice-preset-${preset.id}`;
          return (
            <button
              key={preset.id}
              type="button"
              disabled={disabled}
              onClick={() => onSelect(preset)}
              data-testid={testId}
              className={cn(
                "rounded-full border-0 bg-transparent p-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                disabled && "pointer-events-none opacity-50",
              )}
            >
              <Badge
                variant={isUser ? "secondary" : "outline"}
                className="cursor-pointer text-[10px] font-normal transition-colors hover:bg-secondary/80"
              >
                {preset.label}
              </Badge>
            </button>
          );
        })}
        {onSavePreset ? (
          <Button
            type="button"
            size="sm"
            variant="ghost"
            className="h-6 px-2 text-[10px]"
            disabled={disabled || !canSavePreset}
            onClick={onSavePreset}
            data-testid="save-slice-preset"
          >
            <BookmarkPlus className="h-3 w-3" />
            Save
          </Button>
        ) : null}
      </div>
      {chainButtons.length > 0 ? (
        <div className="flex flex-wrap gap-1.5" role="group" aria-label="Preset chains">
          {chainButtons.map((chain) => (
            <Button
              key={chain.id}
              type="button"
              size="sm"
              variant="outline"
              className="h-7 text-[10px]"
              disabled={disabled}
              onClick={chain.onRun}
              data-testid={`slice-preset-chain-${chain.id}`}
            >
              {chain.label}
            </Button>
          ))}
        </div>
      ) : null}
    </div>
  );
}