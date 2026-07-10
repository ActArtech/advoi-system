/**
 * Playwright stub — PWA voice UI state machine (ship #1).
 *
 * Not wired into CI yet (Playwright is not a project dependency).
 * When enabled: `npx playwright test web/e2e/voice-session-state.spec.ts`
 *
 * Asserts the explicit status chip labels for:
 * idle → connecting → connected → frame_running → confirm_pending → error
 *
 * Screenshot path (manual or when headed): `web/e2e/artifacts/ui-state-chip.png`
 */

import { UI_SESSION_STATES, UI_STATE_LABELS } from "../components/voiceSessionState";

// Minimal type stubs so this file typechecks without @playwright/test installed.
type Page = {
  goto: (url: string) => Promise<unknown>;
  getByTestId: (id: string) => {
    getAttribute: (name: string) => Promise<string | null>;
    textContent: () => Promise<string | null>;
  };
  screenshot: (opts: { path: string; fullPage?: boolean }) => Promise<unknown>;
};
type TestFn = (name: string, fn: (args: { page: Page }) => Promise<void>) => void;
type Expect = (actual: unknown) => {
  toBe: (expected: unknown) => void;
  toContain: (expected: string) => void;
};

declare const test: TestFn & { skip?: TestFn };
declare const expect: Expect;

const BASE = process.env.ADVOI_WEB_URL || "http://localhost:3000";

test("exports the six explicit UI session states with labels", async () => {
  expect(UI_SESSION_STATES.length).toBe(6);
  expect(UI_SESSION_STATES).toContain("idle");
  expect(UI_SESSION_STATES).toContain("connecting");
  expect(UI_SESSION_STATES).toContain("connected");
  expect(UI_SESSION_STATES).toContain("frame_running");
  expect(UI_SESSION_STATES).toContain("confirm_pending");
  expect(UI_SESSION_STATES).toContain("error");
  for (const s of UI_SESSION_STATES) {
    expect(UI_STATE_LABELS[s].length > 0).toBe(true);
  }
});

test("PWA status chip shows Idle on load", async ({ page }) => {
  await page.goto(BASE + "/");
  const chip = page.getByTestId("ui-state-chip");
  expect(await chip.getAttribute("data-state")).toBe("idle");
  const text = (await chip.textContent()) || "";
  expect(text.toLowerCase()).toContain("idle");
  await page.screenshot({ path: "web/e2e/artifacts/ui-state-chip.png", fullPage: false });
});
