import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const desktopRoot = path.resolve(import.meta.dirname, "..");
const source = (relativePath: string) => readFileSync(path.join(desktopRoot, relativePath), "utf8");

describe("screenshot binding wakeup contract", () => {
  it("publishes authoritative binding lifecycle through the preload bridge", () => {
    expect(source("src/main/preload.ts")).toContain('ipcRenderer.send("desktop:screenshot-binding", binding)');
    const renderer = source("src/renderer/CompanionApp.tsx");
    expect(renderer).toContain("publishScreenshotBinding?.(null)");
    expect(renderer).toContain("publishScreenshotBinding?.({ sessionId: binding.sessionId, bindingId: binding.bindingId })");
  });

  it("lets the main process restart a suspended stream without a capture-state transition", () => {
    const main = source("src/main/index.ts");
    expect(main).toContain('ipcMain.on("desktop:screenshot-binding"');
    expect(main).toContain("screenshotBindingTransition(remoteScreenshotBindingKey, nextBindingKey, remoteScreenshotSuspended)");
    expect(main).toContain('transition === "restart" && screenshotStreamEligible(captureState)');
  });
});
