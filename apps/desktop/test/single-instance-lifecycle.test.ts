import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

describe("desktop single-instance lifecycle", () => {
  it("claims the profile lock before readiness and focuses the existing window", () => {
    const source = readFileSync(new URL("../src/main/index.ts", import.meta.url), "utf8");
    const lockIndex = source.indexOf("app.requestSingleInstanceLock");
    const readyIndex = source.indexOf("app.whenReady()");

    expect(lockIndex).toBeGreaterThan(-1);
    expect(readyIndex).toBeGreaterThan(lockIndex);
    expect(source).toContain('app.on("second-instance"');
    expect(source).toContain("if (mainWindow.isMinimized()) mainWindow.restore()");
    expect(source).toContain("mainWindow.show()");
    expect(source).toContain("mainWindow.focus()");
    expect(source).toContain("if (!ownsCompanionInstance) app.quit()");
  });
});
