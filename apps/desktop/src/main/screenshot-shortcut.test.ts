import { describe, expect, it } from "vitest";

import { DEFAULT_SCREENSHOT_SHORTCUT, isSupportedScreenshotShortcut } from "./screenshot-shortcut";

describe("screenshot shortcut presets", () => {
  it("accepts the default and disabled presets", () => {
    expect(isSupportedScreenshotShortcut(DEFAULT_SCREENSHOT_SHORTCUT)).toBe(true);
    expect(isSupportedScreenshotShortcut("")).toBe(true);
  });

  it("rejects arbitrary accelerators", () => {
    expect(isSupportedScreenshotShortcut("CommandOrControl+Q")).toBe(false);
    expect(isSupportedScreenshotShortcut(null)).toBe(false);
  });
});
