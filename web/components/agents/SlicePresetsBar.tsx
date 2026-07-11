"use client";

import { BookmarkPlus, Download, Upload, X } from "lucide-react";
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
  onDeleteUserPreset?: (id: string) => void;
  canSavePreset?: boolean;
  chainButtons?: { id: string; label: string; onRun: () => void }[];
  onExportPresets?: () => void;
  onImportPresets?: () => void;
  disabled?: boolean;
};

export function SlicePresetsBar({
  onSelect,
  userPresets = [],
  onSavePreset,
  onDeleteUserPreset,
  canSavePreset,
  chainButtons = [],
  onExportPresets,
  onImportPresets,
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
            <span key={preset.id} className="inline-flex items-center gap-0.5">
              <button
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
              {isUser && onDeleteUserPreset ? (
                <button
                  type="button"
                  disabled={disabled}
                  aria-label={`Delete ${preset.label}`}
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteUserPreset(preset.id);
                  }}
                  data-testid={`delete-slice-preset-${preset.id}`}
                  className="rounded-full p-0.5 text-muted-foreground hover:bg-destructive/20 hover:text-destructive disabled:opacity-50"
                >
                  <X className="h-3 w-3" />
                </button>
              ) : null}
            </span>
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
      <div className="flex flex-wrap items-center gap-1.5">
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
        {onExportPresets ? (
          <Button
            type="button"
            size="sm"
            variant="ghost"
            className="h-7 text-[10px]"
            disabled={disabled}
            onClick={onExportPresets}
            data-testid="export-user-presets"
          >
            <Download className="h-3 w-3" />
            Export presets
          </Button>
        ) : null}
        {onImportPresets ? (
          <Button
            type="button"
            size="sm"
            variant="ghost"
            className="h-7 text-[10px]"
            disabled={disabled}
            onClick={onImportPresets}
            data-testid="import-user-presets"
          >
            <Upload className="h-3 w-3" />
            Import
          </Button>
        ) : null}
      </div>
    </div>
  );
}