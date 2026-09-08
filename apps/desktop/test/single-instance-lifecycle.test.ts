import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

describe("desktop single-instance lifecycle", () => {
  it("claims one profile owner before readiness and focuses the existing window", () => {
    const source = readFileSync(new URL("../src/main/index.ts", import.meta.url), "utf8");
    const lock = source.indexOf("app.requestSingleInstanceLock");
    const ready = source.indexOf("app.whenReady()");

    expect(lock).toBeGreaterThan(-1);
    expect(ready).toBeGreaterThan(lock);
    expect(source).toContain('app.on("second-instance"');
    expect(source).toContain("mainWindow.restore()");
    expect(source).toContain("mainWindow.show()");
    expect(source).toContain("mainWindow.focus()");
    expect(source).toContain("if (!ownsCompanionInstance) app.quit()");
  });
});
