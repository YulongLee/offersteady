import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  DesktopConnectionRecovery,
  type DesktopConnectionDiagnostic,
  type DesktopRegistrationContext,
} from "../src/main/desktop-connection-recovery";

const deferred = <T>() => {
  let resolve!: (value: T) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<T>((accept, decline) => { resolve = accept; reject = decline; });
  return { promise, resolve, reject };
};

describe("bounded desktop connection recovery", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(1_000);
  });
  afterEach(() => vi.useRealTimers());

  it("keeps ordinary successful heartbeats at 15 seconds with no new polling", async () => {
    const startedAt: number[] = [];
    const coordinator = new DesktopConnectionRecovery({
      register: async () => { startedAt.push(Date.now()); return true; },
    });
    coordinator.start();
    coordinator.start();
    await vi.advanceTimersByTimeAsync(44_999);
    expect(startedAt).toEqual([1_000, 16_000, 31_000]);
    await vi.advanceTimersByTimeAsync(1);
    expect(startedAt).toEqual([1_000, 16_000, 31_000, 46_000]);
    expect(coordinator.snapshot()).toMatchObject({ online: true, attempts: 4, failures: 0 });
    coordinator.dispose();
  });

  it("releases a hung registration after the whole-operation deadline", async () => {
    const contexts: DesktopRegistrationContext[] = [];
    const neverReturns = deferred<boolean>();
    const coordinator = new DesktopConnectionRecovery({
      register: context => {
        contexts.push(context);
        return contexts.length === 1 ? neverReturns.promise : Promise.resolve(true);
      },
    });
    coordinator.start();
    await vi.advanceTimersByTimeAsync(7_999);
    expect(coordinator.snapshot()).toMatchObject({ inFlight: true, online: false });
    await vi.advanceTimersByTimeAsync(1);
    expect(contexts[0]?.signal.aborted).toBe(true);
    expect(contexts[0]?.isCurrent()).toBe(false);
    expect(coordinator.snapshot()).toMatchObject({ inFlight: false, timeouts: 1, lastErrorCode: "registration-timeout" });
    await vi.advanceTimersByTimeAsync(7_000);
    expect(contexts).toHaveLength(2);
    expect(coordinator.snapshot()).toMatchObject({ online: true, inFlight: false, successes: 1 });
    coordinator.dispose();
  });

  it("bounds identity and response consumption, not only the fetch call", async () => {
    const identity = deferred<void>();
    const responseBody = deferred<void>();
    let identityFinished = false;
    let unsafeCommit = false;
    const coordinator = new DesktopConnectionRecovery({
      register: async context => {
        await identity.promise;
        if (!context.isCurrent()) return false;
        identityFinished = true;
        await responseBody.promise;
        if (!context.isCurrent()) return false;
        unsafeCommit = true;
        return true;
      },
    });
    coordinator.start();
    await vi.advanceTimersByTimeAsync(4_000);
    identity.resolve();
    await vi.advanceTimersByTimeAsync(0);
    expect(identityFinished).toBe(true);
    await vi.advanceTimersByTimeAsync(4_000);
    responseBody.resolve();
    await vi.advanceTimersByTimeAsync(0);
    expect(unsafeCommit).toBe(false);
    expect(coordinator.snapshot()).toMatchObject({ successes: 0, timeouts: 1 });
    coordinator.dispose();
  });

  it("merges concurrent resume, online and focus signals into the current successful operation", async () => {
    const pending = deferred<boolean>();
    const register = vi.fn(() => pending.promise);
    const onSuccess = vi.fn();
    const coordinator = new DesktopConnectionRecovery({ register, onSuccess });
    coordinator.start();
    coordinator.recover("resume");
    coordinator.recover("online");
    coordinator.recover("focus");
    await vi.advanceTimersByTimeAsync(1_000);
    expect(register).toHaveBeenCalledTimes(1);
    pending.resolve(true);
    await vi.advanceTimersByTimeAsync(10_000);
    expect(register).toHaveBeenCalledTimes(1);
    expect(onSuccess).toHaveBeenCalledTimes(1);
    expect(coordinator.snapshot().mergedRecoverySignals).toBe(3);
    coordinator.dispose();
  });

  it("coalesces explicit recovery to one request after the two-second minimum", async () => {
    const register = vi.fn(async () => true);
    const coordinator = new DesktopConnectionRecovery({ register });
    coordinator.start();
    await vi.advanceTimersByTimeAsync(0);
    coordinator.recover("resume");
    coordinator.recover("focus");
    coordinator.recover("online");
    await vi.advanceTimersByTimeAsync(1_999);
    expect(register).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(1);
    expect(register).toHaveBeenCalledTimes(2);
    await vi.advanceTimersByTimeAsync(12_999);
    expect(register).toHaveBeenCalledTimes(2);
    await vi.advanceTimersByTimeAsync(1);
    expect(register).toHaveBeenCalledTimes(3);
    coordinator.dispose();
  });

  it("preserves one explicit recovery intent when the current operation fails", async () => {
    const first = deferred<boolean>();
    const register = vi.fn().mockImplementationOnce(() => first.promise).mockResolvedValue(true);
    const coordinator = new DesktopConnectionRecovery({ register });
    coordinator.start();
    coordinator.recover("resume");
    coordinator.recover("focus");
    first.resolve(false);
    await vi.advanceTimersByTimeAsync(1_999);
    expect(register).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(1);
    expect(register).toHaveBeenCalledTimes(2);
    expect(coordinator.snapshot()).toMatchObject({ successes: 1, failures: 1, consecutiveFailures: 0 });
    coordinator.dispose();
  });

  it("discards old success after timeout and a later recovery succeeds", async () => {
    const first = deferred<boolean>();
    const onSuccess = vi.fn();
    const register = vi.fn().mockImplementationOnce(() => first.promise).mockResolvedValue(true);
    const coordinator = new DesktopConnectionRecovery({ register, onSuccess });
    coordinator.start();
    await vi.advanceTimersByTimeAsync(8_000);
    coordinator.recover("resume");
    await vi.advanceTimersByTimeAsync(0);
    const recoveredSnapshot = coordinator.snapshot();
    expect(recoveredSnapshot).toMatchObject({ lastSuccessAtMs: 9_000, successes: 1, timeouts: 1 });
    await vi.advanceTimersByTimeAsync(100);
    first.resolve(true);
    await vi.advanceTimersByTimeAsync(0);
    expect(coordinator.snapshot()).toEqual(recoveredSnapshot);
    expect(onSuccess).toHaveBeenCalledTimes(1);
    coordinator.dispose();
  });

  it("expires overdue work on resume even before suspended timers run", async () => {
    const first = deferred<boolean>();
    let oldContext: DesktopRegistrationContext | undefined;
    const register = vi.fn().mockImplementationOnce((context: DesktopRegistrationContext) => {
      oldContext = context;
      return first.promise;
    }).mockResolvedValue(true);
    const coordinator = new DesktopConnectionRecovery({ register });
    coordinator.start();
    vi.setSystemTime(171_000);
    expect(oldContext?.isCurrent()).toBe(false);
    coordinator.recover("resume");
    await vi.advanceTimersByTimeAsync(0);
    expect(register).toHaveBeenCalledTimes(2);
    expect(coordinator.snapshot()).toMatchObject({ online: true, timeouts: 1, lastSuccessAtMs: 171_000 });
    first.resolve(true);
    await vi.advanceTimersByTimeAsync(0);
    expect(coordinator.snapshot().successes).toBe(1);
    coordinator.dispose();
  });

  it("does not accept an overdue result merely because its timeout callback was delayed", async () => {
    const first = deferred<boolean>();
    const onSuccess = vi.fn();
    const coordinator = new DesktopConnectionRecovery({ register: () => first.promise, onSuccess });
    coordinator.start();
    vi.setSystemTime(10_000);
    first.resolve(true);
    await vi.advanceTimersByTimeAsync(0);
    expect(coordinator.snapshot()).toMatchObject({ online: false, timeouts: 1, successes: 0 });
    expect(onSuccess).not.toHaveBeenCalled();
    coordinator.dispose();
  });

  it("does not claim online after the last success passes the server freshness window", async () => {
    const coordinator = new DesktopConnectionRecovery({ register: async () => true });
    coordinator.start();
    await vi.advanceTimersByTimeAsync(0);
    vi.setSystemTime(45_999);
    expect(coordinator.snapshot().online).toBe(true);
    vi.setSystemTime(46_000);
    expect(coordinator.snapshot().online).toBe(false);
    coordinator.dispose();
  });

  it("does not duplicate a heartbeat immediately after an explicit foreground recovery", async () => {
    const register = vi.fn(async () => true);
    const coordinator = new DesktopConnectionRecovery({ register });
    coordinator.start();
    await vi.advanceTimersByTimeAsync(14_500);
    coordinator.recover("focus");
    await vi.advanceTimersByTimeAsync(500);
    expect(register).toHaveBeenCalledTimes(2);
    await vi.advanceTimersByTimeAsync(15_000);
    expect(register).toHaveBeenCalledTimes(3);
    coordinator.dispose();
  });

  it("clears pending recovery and invalidates all old contexts on stop and restart", async () => {
    const first = deferred<boolean>();
    const contexts: DesktopRegistrationContext[] = [];
    const onSuccess = vi.fn();
    const coordinator = new DesktopConnectionRecovery({
      register: context => {
        contexts.push(context);
        return contexts.length === 1 ? first.promise : Promise.resolve(true);
      },
      onSuccess,
    });
    coordinator.start();
    coordinator.recover("resume");
    coordinator.stop();
    expect(contexts[0]?.signal.aborted).toBe(true);
    expect(contexts[0]?.isCurrent()).toBe(false);
    expect(vi.getTimerCount()).toBe(0);
    coordinator.start();
    await vi.advanceTimersByTimeAsync(0);
    first.resolve(true);
    await vi.advanceTimersByTimeAsync(0);
    expect(onSuccess).toHaveBeenCalledTimes(1);
    expect(coordinator.snapshot()).toMatchObject({ attempts: 2, successes: 1, failures: 0 });
    coordinator.stop();
    expect(contexts[1]?.isCurrent()).toBe(false);
    expect(coordinator.snapshot().online).toBe(false);
  });

  it("cancels deferred recovery on disposal and never restarts or reports a late rejection", async () => {
    const first = deferred<boolean>();
    const onSuccess = vi.fn();
    const register = vi.fn(() => first.promise);
    const coordinator = new DesktopConnectionRecovery({ register, onSuccess });
    coordinator.start();
    await vi.advanceTimersByTimeAsync(8_000);
    coordinator.recover("focus");
    coordinator.dispose();
    coordinator.start();
    coordinator.recover("resume");
    first.reject(new Error("synthetic late failure"));
    await vi.advanceTimersByTimeAsync(60_000);
    expect(register).toHaveBeenCalledTimes(2);
    expect(onSuccess).not.toHaveBeenCalled();
    expect(vi.getTimerCount()).toBe(0);
  });

  it("clears a recovery timer scheduled after a successful operation on dispose", async () => {
    const register = vi.fn(async () => true);
    const coordinator = new DesktopConnectionRecovery({ register });
    coordinator.start();
    await vi.advanceTimersByTimeAsync(0);
    coordinator.recover("focus");
    coordinator.dispose();
    await vi.advanceTimersByTimeAsync(60_000);
    expect(register).toHaveBeenCalledTimes(1);
    expect(vi.getTimerCount()).toBe(0);
  });

  it("invalidates a prior success notification when a newer recovery owns the connection", async () => {
    const notified: DesktopRegistrationContext[] = [];
    const coordinator = new DesktopConnectionRecovery({
      register: async () => true,
      onSuccess: context => notified.push(context),
    });
    coordinator.start();
    await vi.advanceTimersByTimeAsync(0);
    expect(notified[0]?.isCurrent()).toBe(true);
    coordinator.recover("online");
    await vi.advanceTimersByTimeAsync(2_000);
    expect(notified).toHaveLength(2);
    expect(notified[0]?.isCurrent()).toBe(false);
    expect(notified[0]?.signal.aborted).toBe(true);
    expect(notified[1]?.isCurrent()).toBe(true);
    coordinator.dispose();
  });

  it("never notifies success after disposal, including disposal inside a diagnostic sink", async () => {
    const onSuccess = vi.fn();
    let coordinator!: DesktopConnectionRecovery;
    coordinator = new DesktopConnectionRecovery({
      register: async () => true,
      onSuccess,
      onDiagnostic: diagnostic => { if (diagnostic.event === "succeeded") coordinator.dispose(); },
    });
    coordinator.start();
    await vi.advanceTimersByTimeAsync(0);
    expect(onSuccess).not.toHaveBeenCalled();
    expect(vi.getTimerCount()).toBe(0);
  });

  it("logs only fixed counters, times and error codes even when the port throws sensitive text", async () => {
    const diagnostics: DesktopConnectionDiagnostic[] = [];
    const coordinator = new DesktopConnectionRecovery({
      register: async () => { throw new Error("synthetic-secret-token manualCode=123456 deviceId=private content=example"); },
      onDiagnostic: diagnostic => diagnostics.push(diagnostic),
    });
    coordinator.start();
    await vi.advanceTimersByTimeAsync(0);
    expect(coordinator.snapshot().lastErrorCode).toBe("registration-failed");
    const encoded = JSON.stringify(diagnostics);
    for (const forbidden of ["synthetic-secret-token", "manualCode", "deviceId", "content=example", "signal", "stack"]) {
      expect(encoded).not.toContain(forbidden);
    }
    expect(diagnostics.at(-1)).toMatchObject({ type: "desktop-connection", event: "failed", durationMs: 0, failures: 1 });
    coordinator.dispose();
  });

  it("continues heartbeats if notification or diagnostic sinks throw", async () => {
    const register = vi.fn(async () => true);
    const coordinator = new DesktopConnectionRecovery({
      register,
      onSuccess: () => { throw new Error("notification failure"); },
      onDiagnostic: () => { throw new Error("logger failure"); },
    });
    coordinator.start();
    await vi.advanceTimersByTimeAsync(15_000);
    expect(register).toHaveBeenCalledTimes(2);
    expect(coordinator.snapshot()).toMatchObject({ successes: 2, failures: 0, inFlight: false });
    coordinator.dispose();
  });
});
