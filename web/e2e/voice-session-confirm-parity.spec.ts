/**
 * Playwright stub — PWA confirm parity (voice + tap identical copy).
 *
 * Not wired into CI yet. When enabled:
 *   npx playwright test web/e2e/voice-session-confirm-parity.spec.ts
 *
 * Covers:
 * - confirmParity model: voice/tap same copy + Confirm button label
 * - UI panel data-testid="confirm-pending" / "confirm-copy" / "confirm-accept"
 * Screenshot path: web/e2e/artifacts/confirm-parity.png
 */

import {
  CONFIRM_BUTTON_LABEL,
  CONFIRM_BANNER_TITLE,
  confirmCopyFromResponse,
  confirmParityModel,
  assertConfirmCopyParity,
} from "../components/confirmParity";

type Expect = (actual: unknown) => {
  toBe: (expected: unknown) => void;
  toContain: (expected: string) => void;
  toBeTruthy: () => void;
};

declare const test: (name: string, fn: () => void | Promise<void>) => void;
declare const expect: Expect;

test("voice and tap extract identical confirm copy from Guardian prompt", () => {
  const payload = {
    prompt: "To stop the FirstMate fleet loop, say stop fleet confirm.",
    spoken_summary: "ignored when prompt present",
  };
  const voice = confirmCopyFromResponse({ spoken: payload.prompt });
  const tap = confirmCopyFromResponse(payload);
  expect(assertConfirmCopyParity(voice, tap)).toBe(true);
  expect(voice).toBe(tap);
});

test("confirmParityModel exposes Confirm button label and banner title", () => {
  const model = confirmParityModel({
    prompt: "To run Queue deep review, confirm yes on voice or tap again after reviewing.",
    targetKind: "frame",
    targetId: "queue_deep_review",
  });
  expect(model.buttonLabel).toBe(CONFIRM_BUTTON_LABEL);
  expect(model.buttonLabel).toBe("Confirm");
  expect(model.title).toBe(CONFIRM_BANNER_TITLE);
  expect(model.copy).toContain("confirm");
  expect(model.targetKind).toBe("frame");
});

test("frame spoken_summary and voice spoken produce same model copy", () => {
  const gate =
    "To run Queue deep review, confirm yes on voice or tap again after reviewing.";
  const voiceModel = confirmParityModel({
    spoken: gate,
    targetKind: "frame",
    targetId: "queue_deep_review",
  });
  const tapModel = confirmParityModel({
    spoken_summary: gate,
    targetKind: "frame",
    targetId: "queue_deep_review",
  });
  expect(voiceModel.copy).toBe(tapModel.copy);
  expect(voiceModel.buttonLabel).toBe(tapModel.buttonLabel);
});
