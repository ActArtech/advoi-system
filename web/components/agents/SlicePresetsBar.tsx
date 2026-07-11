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
    <div className="space-y-4">
      <div className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Presets
        </p>
        <div
          className="flex flex-wrap gap-2"
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
                    className="cursor-pointer px-2.5 py-1 text-xs font-medium transition-colors hover:bg-secondary/80"
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
                    <X className="h-3.5 w-3.5" />
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
              disabled={disabled || !canSavePreset}
              onClick={onSavePreset}
              data-testid="save-slice-preset"
            >
              <BookmarkPlus className="h-3.5 w-3.5" />
              Save
            </Button>
          ) : null}
          {onToggleChainBuilder ? (
            <Button
              type="button"
              size="sm"
              variant={chainBuilderMode ? "default" : "outline"}
              disabled={disabled}
              onClick={onToggleChainBuilder}
              data-testid="toggle-chain-builder"
            >
              <GitBranch className="h-3.5 w-3.5" />
              Chain builder
            </Button>
          ) : null}
          {chainBuilderMode && onToggleChainDispatch ? (
            <Button
              type="button"
              size="sm"
              variant={chainDispatchAfter ? "default" : "outline"}
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
              disabled={disabled || !canSaveChain}
              onClick={onSaveChain}
              data-testid="save-slice-chain"
            >
              Save chain
            </Button>
          ) : null}
        </div>
      </div>

      <div className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Chains
        </p>
        <div className="flex flex-wrap items-center gap-2">
          {chainButtons.map((chain) => (
            <Button
              key={chain.id}
              type="button"
              size="sm"
              variant="outline"
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
                  <X className="h-3.5 w-3.5" />
                </button>
              ) : null}
            </span>
          ))}
          {chainButtons.length === 0 && userChains.length === 0 ? (
            <p className="text-xs text-muted-foreground">No chains yet. Use Chain builder to add one.</p>
          ) : null}
        </div>
      </div>

      {onExportBundle || onImportBundle || onExportPresets ? (
        <div className="space-y-2 rounded-lg border border-dashed border-border/80 bg-muted/20 p-3">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Backup & restore
          </p>
          <div className="flex flex-wrap gap-2">
            {onExportBundle ? (
              <Button
                type="button"
                size="sm"
                variant="default"
                disabled={disabled}
                onClick={onExportBundle}
                data-testid="export-orchestration-bundle"
              >
                <Download className="h-3.5 w-3.5" />
                Export all
              </Button>
            ) : null}
            {onImportBundle ? (
              <Button
                type="button"
                size="sm"
                variant="secondary"
                disabled={disabled}
                onClick={onImportBundle}
                data-testid="import-orchestration-bundle"
              >
                <Upload className="h-3.5 w-3.5" />
                Import all
              </Button>
            ) : null}
            {onExportPresets ? (
              <Button
                type="button"
                size="sm"
                variant="ghost"
                disabled={disabled}
                onClick={onExportPresets}
                data-testid="export-user-presets"
              >
                Presets
              </Button>
            ) : null}
            {onImportPresets ? (
              <Button
                type="button"
                size="sm"
                variant="ghost"
                disabled={disabled}
                onClick={onImportPresets}
                data-testid="import-user-presets"
              >
                Import presets
              </Button>
            ) : null}
            {onExportChains ? (
              <Button
                type="button"
                size="sm"
                variant="ghost"
                disabled={disabled}
                onClick={onExportChains}
                data-testid="export-user-chains"
              >
                Chains
              </Button>
            ) : null}
            {onImportChains ? (
              <Button
                type="button"
                size="sm"
                variant="ghost"
                disabled={disabled}
                onClick={onImportChains}
                data-testid="import-user-chains"
              >
                Import chains
              </Button>
            ) : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}