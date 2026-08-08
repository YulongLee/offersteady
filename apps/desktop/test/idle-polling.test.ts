import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import {
  BINDING_LIVE_POLL_MS,
  DESKTOP_FAILURE_MAX_POLL_MS,
  DESKTOP_IDLE_POLL_MS,
  SCREENSHOT_LIVE_POLL_MS,
  desktopFailureBackoffMs,
  desktopPollDelayMs,
} from "../src/main/polling-policy";

describe("desktop idle polling policy", () => {
  it("keeps screenshot polling fast only for live bindings", () => {
    expect(desktopPollDelayMs("live", 0, "screenshot")).toBe(SCREENSHOT_LIVE_POLL_MS);
    expect(desktopPollDelayMs("live", 0, "binding")).toBe(BINDING_LIVE_POLL_MS);
    expect(desktopPollDelayMs("idle")).toBe(DESKTOP_IDLE_POLL_MS);
    expect(DESKTOP_IDLE_POLL_MS).toBeGreaterThanOrEqual(10_000);
  });

  it("backs off failures and recovers to the normal interval", () => {
    expect([1, 2, 3, 4, 5].map(desktopFailureBackoffMs)).toEqual([5_000, 10_000, 20_000, 30_000, 30_000]);
    expect(desktopPollDelayMs("failure", 10)).toBe(DESKTOP_FAILURE_MAX_POLL_MS);
    expect(desktopPollDelayMs("idle", 0)).toBe(DESKTOP_IDLE_POLL_MS);
  });

  it("keeps remote screenshot polling in the main process only", () => {
    const mainSource = readFileSync(new URL("../src/main/index.ts", import.meta.url), "utf8");
    const rendererSource = readFileSync(new URL("../src/renderer/CompanionApp.tsx", import.meta.url), "utf8");
    const endpoint = "/capture-requests/next";

    expect(mainSource).toContain(endpoint);
    expect(mainSource).toContain("getDesktopScreenshotPollingState");
    expect(rendererSource).not.toContain(endpoint);
    expect(rendererSource).not.toContain("pollRemoteScreenshotRequests");
  });
});
