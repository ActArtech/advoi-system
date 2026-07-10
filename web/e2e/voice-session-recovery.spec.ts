/**
 * Playwright stub — PWA error recovery paths (ship recovery).
 *
 * Not wired into CI yet. When enabled:
 *   npx playwright test web/e2e/voice-session-recovery.spec.ts
 *
 * Covers recovery panel kinds:
 *   mic_denied | livekit_connect | api_frame
 * with retry + Path C (`/voice-server`) affordances.
 */

import {
  PATH_C_HREF,
  errorRecoveryModel,
  classifyApiError,
  classifyConnectError,
} from "../components/errorRecovery";

type Expect = (actual: unknown) => {
  toBe: (expected: unknown) => void;
  toContain: (expected: string) => void;
  toBeTruthy: () => void;
  toBeFalsy: () => void;
};

declare const test: (name: string, fn: () => void | Promise<void>) => void;
declare const expect: Expect;

test("mic denied recovery: retry, no Path C", () => {
  const input = classifyConnectError(
    Object.assign(new Error("Permission denied"), { name: "NotAllowedError" }),
  );
  const model = errorRecoveryModel(input);
  expect(model.kind).toBe("mic_denied");
  expect(model.showRetry).toBe(true);
  expect(model.showPathC).toBe(false);
});

test("LiveKit connect fail: retry + Path C", () => {
  const input = classifyConnectError(new Error("Token endpoint returned 503"), {
    httpStatus: 503,
  });
  const model = errorRecoveryModel({ ...input, kind: "livekit_connect" });
  expect(model.kind).toBe("livekit_connect");
  expect(model.showRetry).toBe(true);
  expect(model.showPathC).toBe(true);
  expect(model.pathCHref).toBe(PATH_C_HREF);
  expect(model.pathCHref).toContain("voice-server");
});

test("API 502 frame: retry + Path C", () => {
  const input = classifyApiError(new Error("Frame returned 502"), {
    httpStatus: 502,
    target: "fleet_status",
  });
  const model = errorRecoveryModel(input);
  expect(model.kind).toBe("api_frame");
  expect(model.showRetry).toBe(true);
  expect(model.showPathC).toBe(true);
  expect(model.pathCHref).toBe("/voice-server");
});
