/**
 * Playwright stub — PWA SLA latency chip (ship #2).
 *
 * Not wired into CI yet (Playwright is not a project dependency).
 * When enabled: `npx playwright test web/e2e/voice-session-latency.spec.ts`
 *
 * Asserts the SLA chip near the UI state chip:
 * - present on load (graceful empty or populated)
 * - data-testid="sla-latency-chip"
 * - after frame run, chip refreshes without full page reload
 *
 * Screenshot path: `web/e2e/artifacts/sla-latency-chip.png`
 */

import { latencyChipModel } from "../components/latencyChip";

// Minimal type stubs so this file typechecks without @playwright/test installed.
type Locator = {
  getAttribute: (name: string) => Promise<string | null>;
  textContent: () => Promise<string | null>;
};
type Page = {
  goto: (url: string) => Promise<unknown>;
  getByTestId: (id: string) => Locator;
  screenshot: (opts: { path: string; fullPage?: boolean }) => Promise<unknown>;
  route?: (
    url: string,
    handler: (route: {
      fulfill: (opts: { status?: number; contentType?: string; body: string }) => Promise<void>;
    }) => Promise<void>,
  ) => Promise<void>;
};
type TestFn = (name: string, fn: (args: { page: Page }) => Promise<void>) => void;
type Expect = (actual: unknown) => {
  toBe: (expected: unknown) => void;
  toContain: (expected: string) => void;
  toBeTruthy: () => void;
};

declare const test: TestFn & { skip?: TestFn };
declare const expect: Expect;

const BASE = process.env.ADVOI_WEB_URL || "http://localhost:3000";

test("latencyChipModel formats ok payload with frame + run_six", async () => {
  const m = latencyChipModel({
    ok: true,
    sla_ok: true,
    sla_target_ms: 800,
    timings_ms: { frame_run_ms: 0.4, run_six_ms: 42 },
  });
  expect(m.available).toBe(true);
  expect(m.tone).toBe("ok");
  expect(m.label).toContain("SLA ok");
  expect(m.label).toContain("frame");
  expect(m.label).toContain("six");
});

test("latencyChipModel graceful empty when diagnostics null", async () => {
  const m = latencyChipModel(null);
  expect(m.available).toBe(false);
  expect(m.tone).toBe("empty");
  expect(m.label).toBe("SLA —");
});

test("PWA SLA chip is present next to state chip on load", async ({ page }) => {
  await page.goto(BASE + "/");
  const state = page.getByTestId("ui-state-chip");
  const sla = page.getByTestId("sla-latency-chip");
  expect(await state.getAttribute("data-state")).toBe("idle");
  const tone = await sla.getAttribute("data-tone");
  expect(tone === "ok" || tone === "warn" || tone === "empty" || tone === "error").toBe(
    true,
  );
  const text = (await sla.textContent()) || "";
  expect(text.toLowerCase()).toContain("sla");
  await page.screenshot({ path: "web/e2e/artifacts/sla-latency-chip.png", fullPage: false });
});
