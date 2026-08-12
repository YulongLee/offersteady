import { describe, expect, it, vi } from "vitest";

import { checkForWebVersionUpdate, extractModuleEntryUrl, type WebVersionCheckRuntime } from "./web-version-refresh";

function buildRuntime(overrides: Partial<WebVersionCheckRuntime> = {}): WebVersionCheckRuntime {
  return {
    fetchHtml: async () => '<script type="module" src="/assets/index-new.js"></script>',
    currentEntryUrl: () => "/assets/index-old.js",
    reload: vi.fn(),
    getReloadGuard: () => null,
    setReloadGuard: vi.fn(),
    ...overrides,
  };
}

describe("web version refresh", () => {
  it("extracts the production module entry from fresh HTML", () => {
    expect(extractModuleEntryUrl('<html><script type="module" crossorigin src="/assets/index-abc.js"></script></html>')).toBe(
      "/assets/index-abc.js",
    );
  });

  it("does not reload when the running entry matches the latest entry", async () => {
    const runtime = buildRuntime({ currentEntryUrl: () => "/assets/index-new.js" });
    await expect(checkForWebVersionUpdate(runtime)).resolves.toBe(false);
    expect(runtime.reload).not.toHaveBeenCalled();
  });

  it("reloads once when a newly deployed entry is detected", async () => {
    const runtime = buildRuntime();
    await expect(checkForWebVersionUpdate(runtime)).resolves.toBe(true);
    expect(runtime.setReloadGuard).toHaveBeenCalledWith("/assets/index-new.js");
    expect(runtime.reload).toHaveBeenCalledOnce();
  });

  it("does not loop when the same target already triggered a reload", async () => {
    const runtime = buildRuntime({ getReloadGuard: () => "/assets/index-new.js" });
    await expect(checkForWebVersionUpdate(runtime)).resolves.toBe(false);
    expect(runtime.reload).not.toHaveBeenCalled();
  });
});
