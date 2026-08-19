import { describe, expect, it } from "vitest";

import { isFreshShortcutScreenshotAcceptance, SHORTCUT_SCREENSHOT_RECOVERY_POLL_INTERVAL_MS } from "./screenshot-shortcut-feedback";

describe("shortcut screenshot feedback policy", () => {
  it("keeps recovery polling low-frequency because realtime acceptance provides immediate feedback", () => {
    expect(SHORTCUT_SCREENSHOT_RECOVERY_POLL_INTERVAL_MS).toBe(15_000);
  });

  it("accepts current realtime notices but ignores stale history events", () => {
    expect(isFreshShortcutScreenshotAcceptance(9_999, 10_000)).toBe(true);
    expect(isFreshShortcutScreenshotAcceptance(4_999, 10_000)).toBe(false);
  });
});
