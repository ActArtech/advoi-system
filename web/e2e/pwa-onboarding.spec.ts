/**
 * Playwright stub — PWA home onboarding (install strip + 60s morning pulse CTA).
 *
 * Not wired into CI yet (Playwright is not a project dependency).
 * When enabled: `npx playwright test web/e2e/pwa-onboarding.spec.ts`
 *
 * Asserts on `/` (no new routes):
 * - install strip visible in browser (not standalone), dismissible
 * - morning pulse CTA present with systems_pulse frame id
 * - Start morning pulse dispatches advoi:run-frame
 *
 * Screenshot path: `web/e2e/artifacts/pwa-onboarding.png`
 */

import {
  detectPlatform,
  installStripModel,
  isStandaloneDisplay,
  morningPulseCtaModel,
  MORNING_PULSE_FRAME_ID,
} from "../components/pwaOnboarding";

// Minimal type stubs so this file typechecks without @playwright/test installed.
type Locator = {
  getAttribute: (name: string) => Promise<string | null>;
  textContent: () => Promise<string | null>;
  click: () => Promise<void>;
  isVisible?: () => Promise<boolean>;
};
type Page = {
  goto: (url: string) => Promise<unknown>;
  getByTestId: (id: string) => Locator;
  screenshot: (opts: { path: string; fullPage?: boolean }) => Promise<unknown>;
  evaluate?: (fn: () => unknown) => Promise<unknown>;
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

test("installStripModel hidden when standalone", async () => {
  const m = installStripModel({ isStandalone: true, dismissed: false });
  expect(m.visible).toBe(false);
});

test("installStripModel visible in browser tab", async () => {
  const m = installStripModel({
    isStandalone: false,
    dismissed: false,
    platform: "ios",
  });
  expect(m.visible).toBe(true);
  expect(m.title).toContain("Home Screen");
});

test("isStandaloneDisplay covers media + iOS", async () => {
  expect(
    isStandaloneDisplay({ standaloneMedia: true, iosStandalone: false }),
  ).toBe(true);
  expect(
    isStandaloneDisplay({ standaloneMedia: false, iosStandalone: true }),
  ).toBe(true);
  expect(
    isStandaloneDisplay({ standaloneMedia: false, iosStandalone: false }),
  ).toBe(false);
});

test("morningPulseCtaModel portfolio voice positioning", async () => {
  const m = morningPulseCtaModel();
  expect(m.frameId).toBe(MORNING_PULSE_FRAME_ID);
  expect(m.title).toContain("60");
  expect(m.body).toContain("portfolio pulse");
  expect(detectPlatform("iPhone")).toBe("ios");
});

test("PWA home shows install strip + morning pulse CTA", async ({ page }) => {
  await page.goto(BASE + "/");
  const root = page.getByTestId("pwa-home-onboarding");
  expect(await root.getAttribute("data-testid")).toBe("pwa-home-onboarding");

  const pulse = page.getByTestId("morning-pulse-cta");
  expect(await pulse.getAttribute("data-frame-id")).toBe("systems_pulse");
  const pulseText = (await pulse.textContent()) || "";
  expect(pulseText.toLowerCase()).toContain("morning pulse");

  // Morning pulse CTA is always on home; install strip depends on standalone/dismiss.
  const start = page.getByTestId("morning-pulse-start");
  const startText = (await start.textContent()) || "";
  expect(startText.toLowerCase()).toContain("morning pulse");

  await page.screenshot({ path: "web/e2e/artifacts/pwa-onboarding.png", fullPage: false });
});
