/**
 * Playwright stub — /ingest UI lifecycle parity (harvest-baseline F3).
 *
 * Not wired into CI yet (Playwright is not a project dependency).
 * When enabled: `npx playwright test web/e2e/ingest-lifecycle.spec.ts`
 *
 * Pure-helper assertions run without a browser (mirror tests/test_ingest_ui_lifecycle.py).
 * Page assertions need ADVOI_WEB_URL + API:
 * - no auto-dispatch checkbox
 * - per-item triage → needs-review → approve → dispatch-dev
 * - status + error banner (422 ontology, failed items)
 *
 * Manual path (if Playwright unavailable):
 * 1. Open /ingest — confirm no "Dispatch to FirstMate after upload" checkbox
 * 2. Upload a .md with project hint → status uploaded; only Triage button
 * 3. Triage → Needs review → Approve → Dispatch to FirstMate
 * 4. Optional: venture hint `totally-unknown-venture` → banner shows Ontology 422
 *
 * Screenshot path: `web/e2e/artifacts/ingest-lifecycle.png`
 */

import {
  HAPPY_PATH,
  actionUrl,
  actionsForStatus,
  parseApiError,
  statusBadgeTone,
} from "../components/ingestLifecycle";

// Minimal type stubs so this file typechecks without @playwright/test installed.
type Locator = {
  getAttribute: (name: string) => Promise<string | null>;
  textContent: () => Promise<string | null>;
  click: () => Promise<void>;
  isVisible?: () => Promise<boolean>;
  count?: () => Promise<number>;
};
type Page = {
  goto: (url: string) => Promise<unknown>;
  getByTestId: (id: string) => Locator;
  locator: (sel: string) => Locator & { count: () => Promise<number> };
  screenshot: (opts: { path: string; fullPage?: boolean }) => Promise<unknown>;
};
type TestFn = (name: string, fn: (args: { page: Page }) => Promise<void>) => void;
type Expect = (actual: unknown) => {
  toBe: (expected: unknown) => void;
  toContain: (expected: string) => void;
  toBeTruthy: () => void;
  toEqual?: (expected: unknown) => void;
  toBeGreaterThan?: (n: number) => void;
};

declare const test: TestFn & { skip?: TestFn };
declare const expect: Expect;

const BASE = process.env.ADVOI_WEB_URL || "http://localhost:3000";

test("HAPPY_PATH matches API contract", async () => {
  expect(HAPPY_PATH.join(">")).toBe("uploaded>triaged>needs_review>approved>dispatched");
});

test("actionsForStatus maps to API path suffixes", async () => {
  expect(actionsForStatus("uploaded")[0].path).toBe("triage");
  expect(actionsForStatus("triaged")[0].path).toBe("needs-review");
  expect(actionsForStatus("needs_review")[0].path).toBe("approve");
  expect(actionsForStatus("approved")[0].path).toBe("dispatch-dev");
  expect(actionsForStatus("approved")[0].body?.confirmed).toBe(true);
  expect(actionsForStatus("failed").length).toBe(0);
  expect(actionsForStatus("dispatched").length).toBe(0);
});

test("actionUrl builds lifecycle endpoints", async () => {
  const a = actionsForStatus("needs_review")[0];
  expect(actionUrl("/api", "id-1", a)).toBe("/api/ingestion/items/id-1/approve");
});

test("parseApiError surfaces ontology 422", async () => {
  const err = parseApiError(422, {
    detail: "Unknown venture_id: ghost",
    code: "UNKNOWN_VENTURE_ID",
  });
  expect(err.isError).toBe(true);
  expect(err.code).toBe("UNKNOWN_VENTURE_ID");
  expect(err.message).toContain("422");
  expect(err.message).toContain("ghost");
});

test("parseApiError surfaces lifecycle 409", async () => {
  const err = parseApiError(409, {
    detail: "Invalid ingestion transition: 'uploaded' → 'dispatched'",
  });
  expect(err.isError).toBe(true);
  expect(err.message).toContain("uploaded");
});

test("statusBadgeTone marks failed as error", async () => {
  expect(statusBadgeTone("failed")).toBe("error");
  expect(statusBadgeTone("approved")).toBe("ready");
});

test("ingest page has no auto-dispatch checkbox and shows lifecycle chrome", async ({
  page,
}) => {
  await page.goto(BASE + "/ingest");
  const root = page.getByTestId("ingest-page");
  expect(await root.getAttribute("data-testid")).toBe("ingest-page");

  // Dead auto-dispatch control must be gone
  const auto = page.locator('input[type="checkbox"]');
  expect(await auto.count()).toBe(0);

  const form = page.getByTestId("ingest-upload-form");
  expect(await form.getAttribute("data-testid")).toBe("ingest-upload-form");

  const banner = page.getByTestId("ingest-status");
  const text = (await banner.textContent()) || "";
  expect(text.toLowerCase()).toContain("triage");

  await page.screenshot({
    path: "web/e2e/artifacts/ingest-lifecycle.png",
    fullPage: true,
  });
});
