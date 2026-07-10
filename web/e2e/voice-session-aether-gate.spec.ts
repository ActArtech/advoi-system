/**
 * Playwright stub — PWA Aether gate chip (ship #3 / aether-pwa-gate-01).
 *
 * Not wired into CI yet (Playwright is not a project dependency).
 * When enabled: `npx playwright test web/e2e/voice-session-aether-gate.spec.ts`
 *
 * Asserts the gate chip near the UI state / SLA chips:
 * - present on load (graceful empty or populated)
 * - data-testid="aether-gate-chip"
 * - surfaces gate verdict + active_slug from GET /api/aether/status
 *
 * Screenshot path: `web/e2e/artifacts/aether-gate-chip.png`
 */

import { aetherGateChipModel } from "../components/aetherGateChip";

// Minimal type stubs so this file typechecks without @playwright/test installed.
type Locator = {
  getAttribute: (name: string) => Promise<string | null>;
  textContent: () => Promise<string | null>;
};
type Page = {
  goto: (url: string) => Promise<unknown>;
  getByTestId: (id: string) => Locator;
  screenshot: (opts: { path: string; fullPage?: boolean }) => Promise<unknown>;
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

test("aetherGateChipModel formats pass + active_slug", async () => {
  const m = aetherGateChipModel({
    gate: {
      found: true,
      verdict: "pass",
      active_slug: "gem-dev-shop",
    },
    active_venture: { id: "gem-dev-shop", name: "Gem Dev Shop" },
  });
  expect(m.available).toBe(true);
  expect(m.tone).toBe("ok");
  expect(m.label).toContain("Gate pass");
  expect(m.label).toContain("gem-dev-shop");
  expect(m.activeSlug).toBe("gem-dev-shop");
});

test("aetherGateChipModel graceful empty when status null", async () => {
  const m = aetherGateChipModel(null);
  expect(m.available).toBe(false);
  expect(m.tone).toBe("empty");
  expect(m.label).toBe("Gate —");
});

test("PWA Aether gate chip is present next to state chip on load", async ({ page }) => {
  await page.goto(BASE + "/");
  const state = page.getByTestId("ui-state-chip");
  const gate = page.getByTestId("aether-gate-chip");
  expect(await state.getAttribute("data-state")).toBe("idle");
  const tone = await gate.getAttribute("data-tone");
  expect(tone === "ok" || tone === "warn" || tone === "empty" || tone === "error").toBe(
    true,
  );
  const text = (await gate.textContent()) || "";
  expect(text.toLowerCase()).toContain("gate");
  await page.screenshot({ path: "web/e2e/artifacts/aether-gate-chip.png", fullPage: false });
});
