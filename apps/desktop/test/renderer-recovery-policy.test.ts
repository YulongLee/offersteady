import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

import { decideRendererRecovery } from "../src/main/renderer-recovery-policy";

describe("desktop renderer recovery", () => {
  it("allows three recoveries and rejects a crash loop inside one minute", () => {
    let attempts: readonly number[] = [];
    for (const nowMs of [1_000, 2_000, 3_000]) {
      const decision = decideRendererRecovery(attempts, nowMs);
      expect(decision.allowed).toBe(true);
      attempts = decision.attempts;
    }
    expect(decideRendererRecovery(attempts, 4_000).allowed).toBe(false);
  });

  it("forgets attempts outside the rolling recovery window", () => {
    const decision = decideRendererRecovery([1_000, 2_000, 3_000], 63_001);
    expect(decision).toEqual({ allowed: true, attempts: [63_001] });
  });

  it("wires unexpected renderer exits to bounded window recreation", () => {
    const source = readFileSync(new URL("../src/main/index.ts", import.meta.url), "utf8");
    expect(source).toContain('window.webContents.on("render-process-gone"');
    expect(source).toContain('details.reason === "clean-exit"');
    expect(source).toContain("decideRendererRecovery(rendererRecoveryAttempts, Date.now())");
    expect(source).toContain("if (!isQuitting && !mainWindow) createWindow()");
    expect(source).toContain("desktop:renderer-recovery-requested");
    expect(source).toContain("desktop:renderer-recovery-complete");
    expect(source).toContain("realtime recovery confirmed by fresh frame acknowledgement");
    expect(source).toContain("latestRendererHeartbeat?.sessionId");
  });
});
