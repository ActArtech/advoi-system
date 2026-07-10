/**
 * Playwright stub — PWA home open briefs + review queue surface.
 *
 * Not wired into CI yet (Playwright is not a project dependency).
 * When enabled: `npx playwright test web/e2e/pwa-briefs-surface.spec.ts`
 *
 * Asserts on `/` (no navigation to /briefs required):
 * - surface root present
 * - open briefs + review queue sections
 * - mock-model card render via pure helpers
 *
 * Screenshot path: `web/e2e/artifacts/pwa-briefs-surface.png`
 */

import {
  HOME_BRIEFS_LIMIT,
  OPEN_BRIEFS_FRAME_ID,
  homeBriefsSurfaceModel,
  parseOpenBriefsPayload,
  parseReviewQueuePayload,
} from "../components/pwaBriefsSurface";

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
  route?: (url: string, handler: (route: { fulfill: (opts: unknown) => Promise<void> }) => Promise<void>) => Promise<void>;
};
type TestFn = (name: string, fn: (args: { page: Page }) => Promise<void>) => void;
type Expect = (actual: unknown) => {
  toBe: (expected: unknown) => void;
  toContain: (expected: string) => void;
  toBeTruthy: () => void;
  toEqual?: (expected: unknown) => void;
};

declare const test: TestFn & { skip?: TestFn };
declare const expect: Expect;

const BASE = process.env.ADVOI_WEB_URL || "http://localhost:3000";

test("parseOpenBriefsPayload from mock API", async () => {
  const p = parseOpenBriefsPayload({
    briefs: ["Staging catch-up", "Voice launch"],
    count: 2,
    source: "postgres",
  });
  expect(p.briefs.length).toBe(2);
  expect(p.source).toBe("postgres");
});

test("parseReviewQueuePayload from mock API", async () => {
  const p = parseReviewQueuePayload({
    pending: [
      {
        queue_id: 3,
        title: "Deep review",
        status: "pending",
        brief_url: "https://advoi.keyteller.com/briefs/3",
      },
    ],
    count: 1,
  });
  expect(p.pending.length).toBe(1);
  expect(p.pending[0].queue_id).toBe(3);
});

test("homeBriefsSurfaceModel renders cards with mock data", async () => {
  const m = homeBriefsSurfaceModel({
    openBriefs: ["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta"],
    reviewPending: [
      {
        queue_id: 9,
        title: "Queue item",
        status: "pending",
        brief_url: "https://advoi.keyteller.com/briefs/9",
      },
    ],
    openSource: "postgres",
  });
  expect(m.hasAnyCards).toBe(true);
  expect(m.openBriefs.cards.length).toBe(HOME_BRIEFS_LIMIT);
  expect(m.reviewQueue.cards[0].href).toContain("/briefs/9");
  expect(m.openBriefs.frameId).toBe(OPEN_BRIEFS_FRAME_ID);
  expect(m.heading).toContain("Open briefs");
});

test("PWA home shows open briefs + review queue surface", async ({ page }) => {
  await page.goto(BASE + "/");
  const root = page.getByTestId("pwa-home-briefs-surface");
  expect(await root.getAttribute("data-testid")).toBe("pwa-home-briefs-surface");

  const openSec = page.getByTestId("open-briefs-section");
  expect(await openSec.getAttribute("data-testid")).toBe("open-briefs-section");

  const reviewSec = page.getByTestId("review-queue-section");
  expect(await reviewSec.getAttribute("data-testid")).toBe("review-queue-section");

  const hear = page.getByTestId("hear-open-briefs");
  expect(await hear.getAttribute("data-frame-id")).toBe("open_briefs");

  await page.screenshot({
    path: "web/e2e/artifacts/pwa-briefs-surface.png",
    fullPage: false,
  });
});
