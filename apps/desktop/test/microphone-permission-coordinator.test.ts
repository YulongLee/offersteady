import { afterEach, describe, expect, it, vi } from "vitest";
import {
  CapabilityRegistrationQueue, MicrophonePermissionCoordinator, normalizeMicrophonePermission,
  probeMicrophonePermission, type MicrophonePermissionSnapshot,
} from "../src/renderer/microphone-permission-coordinator";

const deferred = <T>() => {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>(done => { resolve = done; });
  return { promise, resolve };
};
const snapshot = (permission: MicrophonePermissionSnapshot["permission"], pending = false) => ({ permission, pending, source: "os" as const });
const settle = async () => { for (let i = 0; i < 12; i++) await Promise.resolve(); };
afterEach(() => vi.useRealTimers());

describe("current microphone permission evidence", () => {
  it("keeps a late OS grant after bounded waiting without false denial or duplicate requests", async () => {
    vi.useFakeTimers();
    const late = deferred<unknown>();
    const read = vi.fn(async () => snapshot("prompt"));
    const request = vi.fn(() => late.promise), probe = vi.fn(), changes = vi.fn();
    const coordinator = new MicrophonePermissionCoordinator({ read, request, probe, onChange: changes });
    const waiting = coordinator.check({ request: true });
    await settle();
    await vi.advanceTimersByTimeAsync(2501);
    expect(await waiting).toMatchObject({ permission: "unknown", pending: true });
    expect(changes.mock.calls.some(([value]) => value.permission === "denied")).toBe(false);
    expect(await coordinator.check({ request: true })).toMatchObject({ permission: "unknown", pending: true });
    late.resolve(snapshot("granted")); await settle();
    expect(changes.mock.lastCall![0]).toMatchObject({ permission: "granted", pending: false });
    expect(request).toHaveBeenCalledOnce(); expect(read).toHaveBeenCalledTimes(2); expect(probe).not.toHaveBeenCalled();
    coordinator.dispose();
  });

  it("does not apply a permission result after this lifecycle is disposed", async () => {
    const late = deferred<unknown>(), changes = vi.fn();
    const coordinator = new MicrophonePermissionCoordinator({ read: () => late.promise, request: vi.fn(), probe: vi.fn(), onChange: changes });
    const waiting = coordinator.check(); const before = changes.mock.calls.length;
    coordinator.dispose(); await waiting;
    late.resolve(snapshot("denied")); await settle();
    expect(changes).toHaveBeenCalledTimes(before);
  });

  it("does not let a prior OS read overwrite newer real capture evidence", async () => {
    const late = deferred<unknown>(), changes = vi.fn();
    const coordinator = new MicrophonePermissionCoordinator({ read: () => late.promise, request: vi.fn(), probe: vi.fn(), onChange: changes });
    const waiting = coordinator.check(); coordinator.record("granted"); await waiting;
    late.resolve(snapshot("denied")); await settle();
    expect(changes.mock.lastCall![0]).toMatchObject({ permission: "granted", source: "media", pending: false });
    coordinator.dispose();
  });

  it("a timed out read cannot keep returning its stale waiting result after real media evidence", async () => {
    vi.useFakeTimers();
    const old = deferred<unknown>(), changes = vi.fn();
    const read = vi.fn().mockReturnValueOnce(old.promise).mockResolvedValue(snapshot("granted"));
    const probe = vi.fn(async () => ({ ...snapshot("granted"), source: "media" as const }));
    const coordinator = new MicrophonePermissionCoordinator({ read, request: vi.fn(), probe, onChange: changes });
    const first = coordinator.check(); await vi.advanceTimersByTimeAsync(2501);
    expect(await first).toMatchObject({ permission: "unknown", pending: true });
    coordinator.record("granted");
    expect(await coordinator.check({ probe: true })).toMatchObject({ permission: "granted", pending: false });
    expect(read).toHaveBeenCalledTimes(2); expect(probe).toHaveBeenCalledOnce();
    old.resolve(snapshot("denied")); await settle();
    expect(changes.mock.lastCall![0]).toMatchObject({ permission: "granted" }); coordinator.dispose();
  });

  it("allows a passive OS refresh to recover a hanging initial read without a media or permission request", async () => {
    vi.useFakeTimers();
    const old = deferred<unknown>(), changes = vi.fn(), request = vi.fn(), probe = vi.fn();
    const read = vi.fn().mockReturnValueOnce(old.promise).mockResolvedValue(snapshot("granted"));
    const coordinator = new MicrophonePermissionCoordinator({ read, request, probe, onChange: changes });
    const first = coordinator.check(); await vi.advanceTimersByTimeAsync(2501); await first;
    expect(await coordinator.check()).toMatchObject({ permission: "granted", pending: false });
    expect(request).not.toHaveBeenCalled(); expect(probe).not.toHaveBeenCalled();
    old.resolve(snapshot("denied")); await settle();
    expect(changes.mock.lastCall![0]).toMatchObject({ permission: "granted" }); coordinator.dispose();
  });

  it("keeps observing a real pending OS request after an inconclusive focus refresh", async () => {
    vi.useFakeTimers();
    const late = deferred<unknown>(), changes = vi.fn();
    const read = vi.fn().mockResolvedValueOnce(snapshot("prompt")).mockResolvedValue({ ...snapshot("prompt"), pending: true });
    const request = vi.fn(() => late.promise);
    const coordinator = new MicrophonePermissionCoordinator({ read, request, probe: vi.fn(), onChange: changes });
    const first = coordinator.check({ request: true }); await vi.advanceTimersByTimeAsync(2501); await first;
    expect(await coordinator.check()).toMatchObject({ pending: true });
    late.resolve(snapshot("granted")); await settle();
    expect(changes.mock.lastCall![0]).toMatchObject({ permission: "granted", pending: false });
    expect(request).toHaveBeenCalledOnce(); coordinator.dispose();
  });

  it("does not duplicate a still pending explicit media probe when rechecked", async () => {
    vi.useFakeTimers();
    const late = deferred<MicrophonePermissionSnapshot>(), probe = vi.fn(() => late.promise);
    const coordinator = new MicrophonePermissionCoordinator({ read: async () => snapshot("granted"), request: vi.fn(), probe, onChange: vi.fn() });
    const first = coordinator.check({ probe: true }); await vi.advanceTimersByTimeAsync(2501); await first;
    expect(await coordinator.check({ probe: true })).toMatchObject({ permission: "granted", pending: true });
    expect(probe).toHaveBeenCalledOnce(); late.resolve({ ...snapshot("granted"), source: "media" }); await settle(); coordinator.dispose();
  });

  it.each(["disposed", "new-evidence"])("cannot start a late permission request or probe after %s", async kind => {
    const late = deferred<unknown>(), request = vi.fn(), probe = vi.fn();
    const coordinator = new MicrophonePermissionCoordinator({ read: () => late.promise, request, probe, onChange: vi.fn() });
    const waiting = coordinator.check({ request: true, probe: true });
    if (kind === "disposed") coordinator.dispose(); else coordinator.record("denied");
    await waiting; late.resolve(snapshot("prompt")); await settle();
    expect(request).not.toHaveBeenCalled(); expect(probe).not.toHaveBeenCalled(); coordinator.dispose();
  });

  it("does not invent a Windows media success from an unknown status and never probes at startup", async () => {
    const changes = vi.fn(), probe = vi.fn();
    const coordinator = new MicrophonePermissionCoordinator({ read: async () => snapshot("unknown"), request: async () => snapshot("unknown"), probe, onChange: changes });
    const result = await coordinator.check({ request: true });
    expect(result).toMatchObject({ permission: "unknown", pending: false }); expect(probe).not.toHaveBeenCalled();
    coordinator.dispose();
  });

  it("performs the media probe only on explicit check and distinguishes availability", async () => {
    const probe = vi.fn(async () => ({ ...snapshot("unavailable"), source: "media" as const }));
    const coordinator = new MicrophonePermissionCoordinator({ read: async () => snapshot("granted"), request: vi.fn(), probe, onChange: vi.fn() });
    expect(await coordinator.check()).toMatchObject({ permission: "granted" }); expect(probe).not.toHaveBeenCalled();
    expect(await coordinator.check({ probe: true })).toMatchObject({ permission: "unavailable" }); expect(probe).toHaveBeenCalledOnce();
    coordinator.dispose();
  });

  it("does not repeatedly prompt or probe a known OS denial", async () => {
    const request = vi.fn(), probe = vi.fn();
    const coordinator = new MicrophonePermissionCoordinator({ read: async () => snapshot("denied"), request, probe, onChange: vi.fn() });
    expect(await coordinator.check({ request: true, probe: true })).toMatchObject({ permission: "denied" });
    expect(request).not.toHaveBeenCalled(); expect(probe).not.toHaveBeenCalled(); coordinator.dispose();
  });

  it("preserves verified media evidence across an unknown read, but current OS denial wins", async () => {
    const read = vi.fn().mockResolvedValueOnce(snapshot("unknown")).mockResolvedValueOnce(snapshot("denied"));
    const coordinator = new MicrophonePermissionCoordinator({ read, request: vi.fn(), probe: vi.fn(), onChange: vi.fn() });
    coordinator.record("granted");
    expect(await coordinator.check()).toMatchObject({ permission: "granted", source: "media" });
    expect(await coordinator.check()).toMatchObject({ permission: "denied", source: "os" }); coordinator.dispose();
  });

  it("fails closed on invalid IPC replies and private exceptions without reflecting their text", async () => {
    expect(normalizeMicrophonePermission({ permission: "private-marker" })).toMatchObject({ permission: "unknown" });
    const changes = vi.fn();
    const coordinator = new MicrophonePermissionCoordinator({ read: async () => { throw new Error("synthetic-secret"); }, request: vi.fn(), probe: vi.fn(), onChange: changes });
    expect(await coordinator.check({ request: true })).toMatchObject({ permission: "unknown", pending: false });
    expect(JSON.stringify(changes.mock.calls)).not.toContain("synthetic-secret"); coordinator.dispose();
  });
});

describe("explicit local media permission probe", () => {
  it("stops every returned track and uses only the selected microphone", async () => {
    const stop = vi.fn(), videoStop = vi.fn();
    const getUserMedia = vi.fn(async () => ({ getAudioTracks: () => [1], getTracks: () => [{ stop }, { stop: videoStop }] } as unknown as MediaStream));
    expect(await probeMicrophonePermission({ getUserMedia }, "synthetic-mic")).toMatchObject({ permission: "granted", source: "media" });
    expect(getUserMedia).toHaveBeenCalledWith({ audio: { deviceId: { exact: "synthetic-mic" } }, video: false });
    expect(stop).toHaveBeenCalledOnce(); expect(videoStop).toHaveBeenCalledOnce();
  });

  it.each([["NotAllowedError", "denied"], ["SecurityError", "denied"], ["NotFoundError", "unavailable"], ["NotReadableError", "unavailable"], ["OverconstrainedError", "unavailable"], ["AbortError", "unavailable"]] as const)("classifies %s without echoing private input", async (name, permission) => {
    const getUserMedia = vi.fn(async () => { throw new DOMException("private-synthetic", name); });
    const result = await probeMicrophonePermission({ getUserMedia });
    expect(result.permission).toBe(permission); expect(JSON.stringify(result)).not.toContain("private-synthetic");
  });

  it("releases media even when it arrives after coordinator disposal", async () => {
    const late = deferred<MediaStream>(), stop = vi.fn();
    const coordinator = new MicrophonePermissionCoordinator({ read: async () => snapshot("granted"), request: vi.fn(), probe: () => probeMicrophonePermission({ getUserMedia: () => late.promise }), onChange: vi.fn() });
    const waiting = coordinator.check({ probe: true }); await settle(); coordinator.dispose(); await waiting;
    late.resolve({ getAudioTracks: () => [1], getTracks: () => [{ stop }] } as unknown as MediaStream); await settle();
    expect(stop).toHaveBeenCalledOnce();
  });
});

describe("capability changes use one serial current registration", () => {
  it("merges changes while in flight and deduplicates equal payloads", async () => {
    const first = deferred<boolean>(), send = vi.fn().mockReturnValueOnce(first.promise).mockResolvedValue(true);
    const queue = new CapabilityRegistrationQueue(send);
    const pending = queue.submit({ microphone: "unknown", systemAudio: "unknown" });
    void queue.submit({ microphone: "granted", systemAudio: "unknown" });
    void queue.submit({ microphone: "granted", systemAudio: "denied" });
    expect(send).toHaveBeenCalledOnce(); first.resolve(true); await pending;
    expect(send.mock.calls).toEqual([[{ microphone: "unknown", systemAudio: "unknown" }], [{ microphone: "granted", systemAudio: "denied" }]]);
    await queue.submit({ systemAudio: "denied", microphone: "granted" }); expect(send).toHaveBeenCalledTimes(2); queue.dispose();
  });

  it("retains a failed value for an existing control cycle without starting timers", async () => {
    vi.useFakeTimers();
    const send = vi.fn().mockResolvedValueOnce(false).mockResolvedValue(true), queue = new CapabilityRegistrationQueue(send);
    await queue.submit({ microphone: "granted" });
    await vi.advanceTimersByTimeAsync(60_000); expect(send).toHaveBeenCalledOnce();
    await queue.flush(); expect(send).toHaveBeenCalledTimes(2); queue.dispose();
  });

  it("does not send an old pending replacement after disposal", async () => {
    const first = deferred<boolean>(), send = vi.fn(() => first.promise), queue = new CapabilityRegistrationQueue(send);
    const pending = queue.submit({ microphone: "unknown" }); void queue.submit({ microphone: "granted" }); queue.dispose();
    first.resolve(true); await pending; expect(send).toHaveBeenCalledOnce();
  });

  it("does not repeat the successful initial registration", async () => {
    const send = vi.fn(), queue = new CapabilityRegistrationQueue(send), initial = { microphone: "unknown" };
    queue.markSuccessful(initial); await queue.submit({ ...initial }); expect(send).not.toHaveBeenCalled(); queue.dispose();
  });
});
