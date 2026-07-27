import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { describe, expect, it } from "vitest";

import { DEFAULT_SCREENSHOT_SHORTCUT, ScreenshotShortcutStore, isSupportedScreenshotShortcut } from "./screenshot-shortcut";

describe("screenshot shortcut presets", () => {
  it("accepts the default and disabled presets", () => {
    expect(isSupportedScreenshotShortcut(DEFAULT_SCREENSHOT_SHORTCUT)).toBe(true);
    expect(isSupportedScreenshotShortcut("")).toBe(true);
  });

  it("rejects arbitrary accelerators", () => {
    expect(isSupportedScreenshotShortcut("CommandOrControl+Q")).toBe(false);
    expect(isSupportedScreenshotShortcut(null)).toBe(false);
  });

  it("migrates the legacy macOS command shortcut to control", async () => {
    const directory = await mkdtemp(path.join(tmpdir(), "offersteady-shortcut-"));
    try {
      await writeFile(
        path.join(directory, "screenshot-shortcut.json"),
        JSON.stringify({ accelerator: "CommandOrControl+Shift+Space" }),
        "utf8",
      );

      await expect(new ScreenshotShortcutStore(directory).load()).resolves.toBe("Control+Shift+Space");
    } finally {
      await rm(directory, { recursive: true, force: true });
    }
  });
});
