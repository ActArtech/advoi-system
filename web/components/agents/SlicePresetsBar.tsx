"use client";

import { BookmarkPlus, Download, GitBranch, Upload, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { allPresetsForBar } from "@/lib/agents/slicePresets";
import type { SlicePreset } from "@/lib/agents/slicePresets";
import type { UserSlicePreset } from "@/lib/agents/customUserPresets";
import type { UserPresetChain } from "@/lib/agents/customUserChains";
import { cn } from "@/lib/utils";

type SlicePresetsBarProps = {
  onSelect: (preset: SlicePreset) => void;
  userPresets?: UserSlicePreset[];
  onSavePreset?: () => void;
  onDeleteUserPreset?: (id: string) => void;
  canSavePreset?: boolean;
  chainButtons?: { id: string; label: string; onRun: () => void }[];
  userChains?: UserPresetChain[];
  onRunUserChain?: (chain: UserPresetChain) => void;
  onDeleteUserChain?: (id: string) => void;
  chainBuilderMode?: boolean;
  onToggleChainBuilder?: () => void;
  chainDraftIds?: string[];
  onToggleChainPreset?: (presetId: string) => void;
  onSaveChain?: () => void;
  canSaveChain?: boolean;
  chainDispatchAfter?: boolean;
  onToggleChainDispatch?: () => void;
  onExportPresets?: () => void;
  onImportPresets?: () => void;
  onExportChains?: () => void;
  onImportChains?: () => void;
  onExportBundle?: () => void;
  onImportBundle?: () => void;
  disabled?: boolean;
};

export function SlicePresetsBar({
  onSelect,
  userPresets = [],
  onSavePreset,
  onDeleteUserPreset,
  canSavePreset,
  chainButtons = [],
  userChains = [],
  onRunUserChain,
  onDeleteUserChain,
  chainBuilderMode = false,
  onToggleChainBuilder,
  chainDraftIds = [],
  onToggleChainPreset,
  onSaveChain,
  canSaveChain,
  chainDispatchAfter = false,
  onToggleChainDispatch,
  onExportPresets,
  onImportPresets,
  onExportChains,
  onImportChains,
  onExportBundle,
  onImportBundle,
  disabled,
}: SlicePresetsBarProps) {
  const allPresets = allPresetsForBar(userPresets);
  const draftSet = new Set(chainDraftIds);

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
          const inDraft = draftSet.has(preset.id);
          const testId = isUser
            ? `slice-preset-user-${preset.id}`
            : `slice-preset-${preset.id}`;
          return (
            <span key={preset.id} className="inline-flex items-center gap-0.5">
              <button
                type="button"
                disabled={disabled}
                onClick={() =>
                  chainBuilderMode && onToggleChainPreset
                    ? onToggleChainPreset(preset.id)
                    : onSelect(preset)
                }
                data-testid={testId}
                data-chain-draft={inDraft ? "true" : "false"}
                className={cn(
                  "rounded-full border-0 bg-transparent p-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                  disabled && "pointer-events-none opacity-50",
                )}
              >
                <Badge
                  variant={inDraft ? "default" : isUser ? "secondary" : "outline"}
                  className="cursor-pointer text-[10px] font-normal transition-colors hover:bg-secondary/80"
                >
                  {inDraft ? `${chainDraftIds.indexOf(preset.id) + 1}. ` : ""}
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
        {onToggleChainBuilder ? (
          <Button
            type="button"
            size="sm"
            variant={chainBuilderMode ? "default" : "ghost"}
            className="h-6 px-2 text-[10px]"
            disabled={disabled}
            onClick={onToggleChainBuilder}
            data-testid="toggle-chain-builder"
          >
            <GitBranch className="h-3 w-3" />
            Chain
          </Button>
        ) : null}
        {chainBuilderMode && onToggleChainDispatch ? (
          <Button
            type="button"
            size="sm"
            variant={chainDispatchAfter ? "default" : "outline"}
            className="h-6 px-2 text-[10px]"
            disabled={disabled}
            onClick={onToggleChainDispatch}
            data-testid="toggle-chain-dispatch-after"
          >
            + Dispatch
          </Button>
        ) : null}
        {chainBuilderMode && onSaveChain ? (
          <Button
            type="button"
            size="sm"
            variant="secondary"
            className="h-6 px-2 text-[10px]"
            disabled={disabled || !canSaveChain}
            onClick={onSaveChain}
            data-testid="save-slice-chain"
          >
            Save chain
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
        {userChains.map((chain) => (
          <span key={chain.id} className="inline-flex items-center gap-0.5">
            <Button
              type="button"
              size="sm"
              variant="secondary"
              className="h-7 text-[10px]"
              disabled={disabled}
              onClick={() => onRunUserChain?.(chain)}
              data-testid={`slice-user-chain-${chain.id}`}
            >
              {chain.label}
              {chain.dispatchAfter ? " → Dispatch" : ""}
            </Button>
            {onDeleteUserChain ? (
              <button
                type="button"
                disabled={disabled}
                aria-label={`Delete chain ${chain.label}`}
                onClick={() => onDeleteUserChain(chain.id)}
                data-testid={`delete-user-chain-${chain.id}`}
                className="rounded-full p-0.5 text-muted-foreground hover:bg-destructive/20 hover:text-destructive disabled:opacity-50"
              >
                <X className="h-3 w-3" />
              </button>
            ) : null}
          </span>
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
            Import presets
          </Button>
        ) : null}
        {onExportChains ? (
          <Button
            type="button"
            size="sm"
            variant="ghost"
            className="h-7 text-[10px]"
            disabled={disabled}
            onClick={onExportChains}
            data-testid="export-user-chains"
          >
            <Download className="h-3 w-3" />
            Export chains
          </Button>
        ) : null}
        {onImportChains ? (
          <Button
            type="button"
            size="sm"
            variant="ghost"
            className="h-7 text-[10px]"
            disabled={disabled}
            onClick={onImportChains}
            data-testid="import-user-chains"
          >
            <Upload className="h-3 w-3" />
            Import chains
          </Button>
        ) : null}
        {onExportBundle ? (
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="h-7 text-[10px]"
            disabled={disabled}
            onClick={onExportBundle}
            data-testid="export-orchestration-bundle"
          >
            <Download className="h-3 w-3" />
            Export all
          </Button>
        ) : null}
        {onImportBundle ? (
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="h-7 text-[10px]"
            disabled={disabled}
            onClick={onImportBundle}
            data-testid="import-orchestration-bundle"
          >
            <Upload className="h-3 w-3" />
            Import all
          </Button>
        ) : null}
      </div>
    </div>
  );
}