import { describe, expect, it, vi } from "vitest";

import { canAcquireDisplaySources, resolveDisplayMediaSource } from "../src/main/display-media-access";

describe("display media permission containment", () => {
  it("does not acquire macOS display sources while permission is denied", async () => {
    const getSources = vi.fn(async () => [{ id: "screen:1" }]);
    expect(canAcquireDisplaySources("darwin", "denied")).toBe(false);
    await expect(resolveDisplayMediaSource({
      platform: "darwin",
      permissionStatus: "denied",
      getSources,
      sourceId: source => source.id,
    })).resolves.toEqual({ kind: "permission-required" });
    expect(getSources).not.toHaveBeenCalled();
  });

  it("contains display-source rejection as an unavailable result", async () => {
    const failure = new Error("Failed to get sources.");
    await expect(resolveDisplayMediaSource({
      platform: "darwin",
      permissionStatus: "granted",
      getSources: async () => { throw failure; },
      sourceId: source => String(source),
    })).resolves.toEqual({ kind: "unavailable", error: failure });
  });

  it("selects the preferred source after permission is granted", async () => {
    const result = await resolveDisplayMediaSource({
      platform: "darwin",
      permissionStatus: "granted",
      getSources: async () => [{ id: "screen:1" }, { id: "screen:2" }],
      preferredSourceId: "screen:2",
      sourceId: source => source.id,
    });
    expect(result).toEqual({ kind: "ready", source: { id: "screen:2" } });
  });
});
