import { afterEach, describe, expect, it, vi } from "vitest";
import { createMicrophonePermissionRequest } from "../src/main/microphone-permission";
import { MicrophonePermissionController, type MicrophonePermissionState } from "../src/renderer/microphone-permission";

const deferred = <T,>() => {
  let resolve!: (value: T) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
};
afterEach(() => vi.useRealTimers());

describe("OS microphone consent single flight", () => {
  it("waits for delayed consent and deduplicates simultaneous callers", async () => {
    vi.useFakeTimers();
    const answer = deferred<boolean>();
    const ask = vi.fn(() => answer.promise);
    const request = createMicrophonePermissionRequest(() => "not-determined", ask);
    const first = request();
    expect(request()).toBe(first);
    await vi.advanceTimersByTimeAsync(10_000);
    expect(ask).toHaveBeenCalledTimes(1);
    answer.resolve(true);
    expect(await first).toBe(true);
  });

  it.each(["granted", "denied", "restricted"])("uses existing %s status without another prompt", async status => {
    const ask = vi.fn();
    expect(await createMicrophonePermissionRequest(() => status, ask)()).toBe(status === "granted");
    expect(ask).not.toHaveBeenCalled();
  });

  it("allows retry after a failed native call", async () => {
    const ask = vi.fn().mockRejectedValueOnce(new Error("IPC")).mockResolvedValueOnce(true);
    const request = createMicrophonePermissionRequest(() => "not-determined", ask);
    await expect(request()).rejects.toThrow("IPC");
    expect(await request()).toBe(true);
    expect(ask).toHaveBeenCalledTimes(2);
  });
});

describe("truthful microphone permission state", () => {
  it("remains pending beyond ten seconds and accepts the late OS grant", async () => {
    vi.useFakeTimers();
    const answer = deferred<boolean>();
    let status = "not-determined";
    const states: MicrophonePermissionState[] = [];
    const request = vi.fn(() => answer.promise);
    const control = new MicrophonePermissionController({ read: async () => status, request, openSettings: vi.fn() }, state => states.push(state));
    await control.refresh(true);
    const pending = control.request();
    await vi.advanceTimersByTimeAsync(10_000);
    expect(states.at(-1)).toBe("pending");
    expect(request).toHaveBeenCalledTimes(1);
    await control.refresh();
    expect(states.at(-1)).toBe("pending");
    status = "granted";
    answer.resolve(true);
    await pending;
    expect(states.at(-1)).toBe("granted");
    expect(states).not.toContain("denied");
  });

  it.each(["denied", "restricted", "granted"])("does not auto-prompt for %s", async status => {
    const onState = vi.fn(), request = vi.fn();
    const control = new MicrophonePermissionController({ read: async () => status, request, openSettings: vi.fn() }, onState);
    await control.refresh(true);
    expect(onState).toHaveBeenLastCalledWith(status);
    expect(request).not.toHaveBeenCalled();
  });

  it("keeps failed checks distinct from user denial and can recover", async () => {
    const onState = vi.fn();
    const read = vi.fn().mockRejectedValueOnce(Error("IPC")).mockResolvedValue("granted");
    const control = new MicrophonePermissionController({ read, request: vi.fn(), openSettings: vi.fn() }, onState);
    await control.refresh();
    expect(onState).toHaveBeenLastCalledWith("error");
    await control.refresh();
    expect(onState).toHaveBeenLastCalledWith("granted");
  });

  it("does not invent denial when a request returns without a definitive OS decision", async () => {
    const onState = vi.fn();
    const control = new MicrophonePermissionController({ read: async () => "not-determined", request: async () => false, openSettings: vi.fn() }, onState);
    await control.request();
    expect(onState).toHaveBeenLastCalledWith("not-determined");
  });

  it("ignores a stale read after a newer permission result", async () => {
    const oldRead = deferred<string>(), onState = vi.fn();
    const read = vi.fn().mockReturnValueOnce(oldRead.promise).mockResolvedValue("granted");
    const control = new MicrophonePermissionController({ read, request: vi.fn(), openSettings: vi.fn() }, onState);
    const old = control.refresh();
    await control.refresh();
    oldRead.resolve("denied");
    await old;
    expect(onState).toHaveBeenCalledTimes(1);
    expect(onState).toHaveBeenLastCalledWith("granted");
  });

  it("does not publish a late request result after unmount", async () => {
    const answer = deferred<boolean>(), onState = vi.fn();
    const control = new MicrophonePermissionController({ read: async () => "granted", request: () => answer.promise, openSettings: vi.fn() }, onState);
    const pending = control.request();
    control.dispose();
    answer.resolve(true);
    await pending;
    expect(onState.mock.calls).toEqual([["pending"]]);
  });

  it("does not replace a newer OS grant with an old request failure", async () => {
    const answer = deferred<boolean>(), onState = vi.fn();
    const control = new MicrophonePermissionController({ read: async () => "granted", request: () => answer.promise, openSettings: vi.fn() }, onState);
    const pending = control.request();
    await control.refresh();
    answer.reject(Error("late IPC failure"));
    await pending;
    expect(onState).toHaveBeenLastCalledWith("granted");
    expect(onState.mock.calls.flat()).not.toContain("error");
  });

  it("surfaces request and settings failures as recoverable errors", async () => {
    const onState = vi.fn();
    const control = new MicrophonePermissionController({ read: async () => "not-determined", request: async () => { throw Error("IPC"); }, openSettings: async () => { throw Error("settings"); } }, onState);
    await control.request();
    expect(onState).toHaveBeenLastCalledWith("error");
    await control.openSettings();
    expect(onState).toHaveBeenLastCalledWith("error");
  });
});
