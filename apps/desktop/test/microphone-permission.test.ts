import { describe, expect, it, vi } from "vitest";
import { MicrophonePermissionController } from "../src/main/microphone-permission";

describe("truthful main process microphone permission", () => {
  it.each(["darwin", "win32"])("reads actual OS denial on %s", platform => {
    const controller = new MicrophonePermissionController({ platform, readStatus: () => "denied", requestAccess: vi.fn() });
    expect(controller.snapshot()).toEqual({ permission: "denied", pending: false, source: "os" });
  });
  it("never converts unknown Windows status into a grant or a Mac request", async () => {
    const request = vi.fn();
    const controller = new MicrophonePermissionController({ platform: "win32", readStatus: () => "unknown", requestAccess: request });
    expect((await controller.request()).permission).toBe("unknown"); expect(request).not.toHaveBeenCalled();
  });
  it("keeps a single long-running Mac request and accepts late consent", async () => {
    let state = "not-determined", resolve!: (value: boolean) => void;
    const request = vi.fn(() => new Promise<boolean>(done => { resolve = done; }));
    const controller = new MicrophonePermissionController({ platform: "darwin", readStatus: () => state, requestAccess: request });
    const first = controller.request(), second = controller.request();
    await Promise.resolve();
    expect(first).toBe(second); expect(controller.snapshot()).toEqual({ permission: "prompt", pending: true, source: "os" });
    state = "granted"; resolve(true);
    expect(await first).toEqual({ permission: "granted", pending: false, source: "os" }); expect(request).toHaveBeenCalledOnce();
  });
  it("reads the final denial without repeated system requests", async () => {
    let state = "not-determined";
    const request = vi.fn(async () => { state = "denied"; return false; });
    const c = new MicrophonePermissionController({ platform: "darwin", readStatus: () => state, requestAccess: request });
    expect((await c.request()).permission).toBe("denied"); await c.request(); expect(request).toHaveBeenCalledOnce();
  });
  it("maps restriction to denial, read errors to unavailable and unsupported platforms to unknown", () => {
    const make = (platform: string, readStatus: () => string) => new MicrophonePermissionController({ platform, readStatus, requestAccess: vi.fn() });
    expect(make("darwin", () => "restricted").snapshot().permission).toBe("denied");
    expect(make("win32", () => { throw new Error("synthetic"); }).snapshot().permission).toBe("unavailable");
    expect(make("linux", () => "granted").snapshot()).toMatchObject({ permission: "unknown", source: "unverified" });
  });
  it("an OS request failure is not fabricated as permission denial", async () => {
    const c = new MicrophonePermissionController({ platform: "darwin", readStatus: () => "not-determined", requestAccess: async () => { throw new Error("synthetic"); } });
    expect(await c.request()).toEqual({ permission: "unavailable", pending: false, source: "unverified" }); expect(c.snapshot().pending).toBe(false);
  });
});
