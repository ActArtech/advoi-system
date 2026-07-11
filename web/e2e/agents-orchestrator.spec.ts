/**
 * Agents tab slice orchestrator tests (logic + optional browser smoke).
 *
 * Run: `npm run test:e2e:agents` from web/
 * Browser smoke requires ADVOI_WEB_URL and skips in CI unless set.
 */

import { test, expect } from "@playwright/test";
import {
  chunkFrameWaves,
  describeWavePlan,
  frameIdsFromFailedResults,
  resolveOrchestrateFrameIds,
  DEFAULT_SIX_FRAME_IDS,
} from "../lib/agents/agentSlices";
import { chainDraftLabel } from "../lib/agents/customUserChains";
import { SLICE_PRESETS, presetById } from "../lib/agents/slicePresets";
import { PRESET_CHAINS, chainById } from "../lib/agents/presetChain";
import {
  bumpQueueItem,
  createQueueEntry,
  enqueueSliceRun,
  queueItemSnapshots,
  removeQueueItem,
} from "../lib/agents/sliceRunQueue";
import {
  detectVoiceMirrorComplete,
  frameIdToPresetId,
  shouldMirrorVoiceFrame,
  voiceMirrorResultFromAgent,
} from "../lib/agents/voiceFrameBridge";

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

test("slice run queue enqueue remove bump snapshots", async () => {
  const a = createQueueEntry("A", async () => {});
  const b = createQueueEntry("B", async () => {});
  const c = createQueueEntry("C", async () => {});
  let q = enqueueSliceRun([], a);
  q = enqueueSliceRun(q, b);
  q = enqueueSliceRun(q, c);
  expect(queueItemSnapshots(q).map((x) => x.label)).toEqual(["A", "B", "C"]);
  q = removeQueueItem(q, b.id);
  expect(queueItemSnapshots(q).map((x) => x.label)).toEqual(["A", "C"]);
  q = bumpQueueItem(q, c.id);
  expect(queueItemSnapshots(q).map((x) => x.label)).toEqual(["C", "A"]);
});

test("chainDraftLabel joins preset labels", async () => {
  const label = chainDraftLabel(["morning_pulse", "ops_core"], SLICE_PRESETS);
  expect(label).toContain("Morning pulse");
  expect(label).toContain("Ops core");
});

test("voice mirror detects completion and result", async () => {
  expect(shouldMirrorVoiceFrame({ frameId: "systems_pulse", source: "morning_pulse_cta" })).toBe(
    true,
  );
  expect(shouldMirrorVoiceFrame({ frameId: "systems_pulse", source: "agents_orchestrator" })).toBe(
    false,
  );
  expect(frameIdToPresetId("systems_pulse")).toBe("morning_pulse");
  const agents = [
    {
      id: "systems-pulse",
      frame_id: "systems_pulse",
      last_run: { status: "ok", spoken_summary: "Pulse ok", timestamp: 2000 },
    },
  ];
  expect(detectVoiceMirrorComplete("systems_pulse", agents, 1000)).toBe(true);
  expect(detectVoiceMirrorComplete("systems_pulse", agents, 3000)).toBe(false);
  const result = voiceMirrorResultFromAgent("systems_pulse", agents);
  expect(result?.spoken_summary).toBe("Pulse ok");
});

test("agents tab shows orchestrator and wave preview", async ({ page }) => {
  test.skip(!process.env.ADVOI_WEB_URL, "Set ADVOI_WEB_URL to run browser smoke");
  await page.goto(process.env.ADVOI_WEB_URL!);
  await page.getByRole("tab", { name: "Agents" }).click();
  await expect(page.getByTestId("agents-orchestrator")).toBeVisible();
  await page.getByTestId("run-mode-stagger").click();
  await expect(page.getByTestId("slice-wave-preview")).toBeVisible();
  await page.screenshot({ path: "e2e/artifacts/agents-orchestrator.png", fullPage: true });
});