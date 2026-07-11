/**
 * Playwright stub — Agents tab slice orchestrator (wave preview, modes, cancel/retry).
 *
 * Not wired into CI yet (Playwright is not a project dependency).
 * When enabled: `npx playwright test web/e2e/agents-orchestrator.spec.ts`
 *
 * Asserts on `/` Agents tab:
 * - agents-orchestrator visible after tab switch
 * - slice-wave-preview shows six default waves in stagger mode
 * - run-mode buttons and run-all-six present
 *
 * Screenshot path: `web/e2e/artifacts/agents-orchestrator.png`
 */

import {
  chunkFrameWaves,
  describeWavePlan,
  frameIdsFromFailedResults,
  resolveOrchestrateFrameIds,
  DEFAULT_SIX_FRAME_IDS,
} from "../lib/agents/agentSlices";
import { SLICE_PRESETS, presetById } from "../lib/agents/slicePresets";
import { PRESET_CHAINS, chainById } from "../lib/agents/presetChain";

type Locator = {
  getAttribute: (name: string) => Promise<string | null>;
  textContent: () => Promise<string | null>;
  click: () => Promise<void>;
  isVisible?: () => Promise<boolean>;
};
type Page = {
  goto: (url: string) => Promise<unknown>;
  getByTestId: (id: string) => Locator;
  getByRole: (role: string, opts?: { name?: string }) => Locator;
  screenshot: (opts: { path: string; fullPage?: boolean }) => Promise<unknown>;
};
type TestFn = (name: string, fn: (args: { page: Page }) => Promise<void>) => void;
type Expect = (actual: unknown) => {
  toBe: (expected: unknown) => void;
  toContain: (expected: string) => void;
  toBeTruthy: () => void;
  toHaveLength: (n: number) => void;
};

declare const test: TestFn & { skip?: TestFn };
declare const expect: Expect;

const BASE = process.env.ADVOI_WEB_URL || "http://localhost:3000";

test("describeWavePlan stagger yields six waves", async () => {
  const plan = describeWavePlan([...DEFAULT_SIX_FRAME_IDS], "stagger");
  expect(plan.waveCount).toBe(6);
  expect(plan.waves[0].labels[0]).toBe("fleet");
});

test("chunkFrameWaves wave mode batches by two", async () => {
  const waves = chunkFrameWaves([...DEFAULT_SIX_FRAME_IDS], "wave");
  expect(waves).toHaveLength(3);
});

test("frameIdsFromFailedResults filters errors", async () => {
  const ids = frameIdsFromFailedResults([
    { frame_id: "fleet_status", status: "ok" },
    { frame_id: "open_briefs", status: "error" },
  ]);
  expect(ids).toContain("open_briefs");
});

test("resolveOrchestrateFrameIds defaults to six", async () => {
  const ids = resolveOrchestrateFrameIds([], "selected");
  expect(ids).toHaveLength(6);
});

test("preset chain ops_then_intel resolves two stages", async () => {
  const chain = chainById("ops_then_intel");
  expect(chain?.presetIds).toHaveLength(2);
  expect(PRESET_CHAINS.length).toBe(5);
});

test("morning_then_full chain has two presets", async () => {
  const chain = chainById("morning_then_full");
  expect(chain?.presetIds).toHaveLength(2);
});

test("intel_then_dispatch chain dispatches after intel", async () => {
  const chain = chainById("intel_then_dispatch");
  expect(chain?.dispatchAfter).toBe(true);
  expect(chain?.presetIds[0]).toBe("intel");
});

test("full_six_then_dispatch chain has dispatchAfter", async () => {
  const chain = chainById("full_six_then_dispatch");
  expect(chain?.dispatchAfter).toBe(true);
});

test("slice presets cover morning pulse and full six", async () => {
  expect(SLICE_PRESETS.length).toBe(4);
  const morning = presetById("morning_pulse");
  expect(morning?.frameIds).toContain("systems_pulse");
  expect(morning?.mode).toBe("stagger");
  const full = presetById("full_six");
  expect(full?.frameIds).toHaveLength(6);
  expect(full?.mode).toBe("parallel");
});

test.skip?.("agents tab shows orchestrator and wave preview", async ({ page }) => {
  await page.goto(BASE);
  await page.getByRole("tab", { name: "Agents" }).click();
  const root = page.getByTestId("agents-orchestrator");
  expect(await root.isVisible?.()).toBeTruthy();
  await page.getByTestId("run-mode-stagger").click();
  const preview = page.getByTestId("slice-wave-preview");
  expect(await preview.isVisible?.()).toBeTruthy();
  await page.screenshot({ path: "web/e2e/artifacts/agents-orchestrator.png", fullPage: true });
});