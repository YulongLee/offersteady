import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { afterEach, describe, expect, it, vi } from "vitest";
import { screenshotBindingKey, screenshotStreamEligible } from "../src/main/screenshot-stream-policy";
import type { WrittenScreenshotJob, WrittenScreenshotPorts } from "../src/main/written-screenshot-processor";

const ts = createRequire(import.meta.url)("typescript") as typeof import("typescript");

const identity = { deviceId: "synthetic-device", manualCode: "synthetic-code" };
const binding = { ...identity, ownerUserId: "synthetic-account", sessionId: "synthetic-current-session", bindingId: "synthetic-current-binding" };
const currentJob: WrittenScreenshotJob = {
  identity, requestId: "synthetic-current-request", generation: 2,
  bindingKey: screenshotBindingKey(binding)!,
};
const pairingData = { registered: true, bound: true, sessionStatus: "live", sessionMode: "written", binding };
const canonicalData = { ...identity, ownerUserId: binding.ownerUserId, sessionId: binding.sessionId, requestId: currentJob.requestId, status: "requested" };
const deferred = <T>() => {
  let resolve!: (value: T) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<T>((accept, decline) => { resolve = accept; reject = decline; });
  return { promise, resolve, reject };
};
const response = (data: unknown, status = 200, timestamp?: string) => new Response(JSON.stringify({ data, ...(timestamp ? { timestamp } : {}) }), { status, headers: { "Content-Type": "application/json" } });

// Exercise the actual main-process admission functions without loading Electron,
// creating windows, or contacting a server. Port callbacks are captured verbatim.
const source = readFileSync(new URL("../src/main/index.ts", import.meta.url), "utf8");
const start = source.indexOf("interface WrittenBinding");
const end = source.indexOf("const enqueueWrittenScreenshot =", start);
if (start < 0 || end < 0) throw new Error("written main admission source boundaries missing");
const compiled = ts.transpileModule(source.slice(start, end), {
  compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS },
}).outputText;
const pollStart = source.indexOf("const pollRemoteScreenshotRequest =");
const pollEnd = source.indexOf("class RemoteScreenshotAdmissionError", pollStart);
if (pollStart < 0 || pollEnd < 0) throw new Error("written main pending probe source boundaries missing");
const compiledPoll = ts.transpileModule(source.slice(pollStart, pollEnd), {
  compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS },
}).outputText;

const harness = (options: {
  pairing?: unknown;
  canonical?: unknown;
  timestamp?: string;
  fetch?: (input: string, init?: RequestInit) => Promise<Response>;
} = {}) => {
  const fetch = vi.fn(options.fetch ?? (async (input: string) => response(input.includes("pairing-status")
    ? options.pairing === undefined ? pairingData : options.pairing
    : options.canonical === undefined ? canonicalData : options.canonical, 200, options.timestamp)));
  const awake = vi.fn();
  const restart = vi.fn();
  const process = vi.fn(async () => true);
  class CapturePorts {
    constructor(readonly ports: WrittenScreenshotPorts<unknown>) {}
    snapshot() { return { pendingCount: 0, activeRequestId: null }; }
  }
  const main = new Function("WrittenScreenshotProcessor", "fetch", "screenshotBindingKey", "screenshotStreamEligible", "desktopApiUrl", "dependencies", `
    let isQuitting = false;
    let screenshotSessionMode = "written";
    let captureState = "paused";
    let remoteScreenshotBindingKey = dependencies.bindingKey;
    let writtenScreenshotGeneration = 2;
    let writtenPendingProbeScheduled = false;
    let remoteScreenshotSuspended = true;
    const writtenCaptureOwners = new Map();
    const app = { getName: () => "Synthetic Companion" };
    const pairingIdentityStore = { loadOrCreate: async () => dependencies.identity };
    const writtenAwake = { refresh: dependencies.awake };
    const startRemoteScreenshotRequestLoop = dependencies.restart;
    const mainWindow = null;
    let processingRemoteScreenshotRequestId = null;
    const processRemoteScreenshotRequest = dependencies.process;
    const getDesktopScreenshotPollingState = async () => ({ live: true, identity: dependencies.identity });
    const screenshotCaptureLock = { ownerToken: () => null, state: () => ({ locked: false }) };
    const releaseScreenshotCaptureLock = () => undefined;
    const fetchWithTimeout = fetch;
    ${compiled}
    ${compiledPoll}
    return {
      inspect: writtenScreenshotProcessor.ports.inspect,
      recover: recoverWrittenScreenshotConnection,
      poll: pollRemoteScreenshotRequest,
      probe: scheduleWrittenPendingProbe,
      setGeneration: value => { writtenScreenshotGeneration = value; },
      setBindingKey: value => { remoteScreenshotBindingKey = value; },
      setMode: value => { screenshotSessionMode = value; },
      setState: value => { captureState = value; },
    };
  `)(CapturePorts, fetch, screenshotBindingKey, screenshotStreamEligible,
    (value: string) => `https://synthetic.invalid/api/v1${value}`,
    { identity, bindingKey: currentJob.bindingKey, awake, restart, process }) as {
      inspect: WrittenScreenshotPorts<unknown>["inspect"];
      recover: (context: { signal: AbortSignal; isCurrent: () => boolean }) => Promise<void>;
      poll: (lockAlreadyHeld?: boolean, excludedRequestId?: string) => Promise<unknown>;
      probe: (excludedRequestId: string) => void;
      setGeneration: (value: number) => void;
      setBindingKey: (value: string | null) => void;
      setMode: (value: string | null) => void;
      setState: (value: string) => void;
    };
  return { ...main, fetch, awake, restart, process };
};

afterEach(() => vi.useRealTimers());

const loopStart = source.indexOf("const startRemoteScreenshotRequestLoop =");
const loopEnd = source.indexOf("const createWindow =", loopStart);
if (loopStart < 0 || loopEnd < 0) throw new Error("written main event loop source boundaries missing");
const compiledLoop = ts.transpileModule(source.slice(loopStart, loopEnd), {
  compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS },
}).outputText;
const loopHarness = (getState: () => Promise<{ live: boolean; identity: typeof identity }>) => {
  const consume = vi.fn(async () => new Promise<void>(() => {}));
  const poll = vi.fn(async () => undefined);
  const runtime = new Function("dependencies", `
    let isQuitting = false;
    let remoteScreenshotLoopGeneration = 0;
    let screenshotRequestTimer = null;
    let remoteScreenshotStreamController = null;
    let remoteScreenshotPollFailureCount = 0;
    let remoteScreenshotSuspended = false;
    let remoteScreenshotPollOwner = null;
    const getDesktopScreenshotPollingState = dependencies.getState;
    const consumeRemoteScreenshotEventStream = dependencies.consume;
    const pollRemoteScreenshotRequest = dependencies.poll;
    const desktopPollDelayMs = () => 15_000;
    const screenshotStreamAdmissionAction = () => "retry";
    const console = { info: () => undefined, warn: () => undefined };
    class RemoteScreenshotAdmissionError extends Error {}
    ${compiledLoop}
    return {
      start: startRemoteScreenshotRequestLoop,
      stop: stopRemoteScreenshotRequestLoop,
      owner: () => remoteScreenshotPollOwner,
      generation: () => remoteScreenshotLoopGeneration,
    };
  `)({ getState, consume, poll }) as { start: () => void; stop: () => void; owner: () => number | null; generation: () => number };
  return { ...runtime, consume, poll };
};

describe("actual written main-process request admission", () => {
  it("admits only the current requested capture using the existing device credentials", async () => {
    const main = harness();
    const result = await main.inspect(currentJob, new AbortController().signal);
    expect(result).toEqual({ current: true, requested: true });
    expect(main.fetch).toHaveBeenCalledTimes(2);
    const canonicalCall = main.fetch.mock.calls.find(([url]) => url.includes("capture-requests/next"));
    expect(canonicalCall).toBeDefined();
    const url = new URL(canonicalCall![0]);
    expect(url.pathname).toContain(`/desktop-devices/${identity.deviceId}/capture-requests/next`);
    expect(url.searchParams.get("manualCode")).toBe(identity.manualCode);
    expect(url.searchParams.get("sessionId")).toBe(binding.sessionId);
    expect(url.searchParams.get("requestId")).toBe(currentJob.requestId);
    expect(canonicalCall![1]?.signal).toBeInstanceOf(AbortSignal);
  });

  it.each([
    { sessionId: "synthetic-ended-session" },
    { deviceId: "synthetic-other-device" },
    { manualCode: "synthetic-other-code" },
    { ownerUserId: "synthetic-other-account" },
    { sessionId: undefined },
    { deviceId: undefined },
    { manualCode: undefined },
    { ownerUserId: undefined },
  ])("rejects a canonical request outside the verified session and device: %j", async mismatch => {
    const main = harness({ canonical: { ...canonicalData, ...mismatch } });
    await expect(main.inspect(currentJob, new AbortController().signal)).rejects.toThrow("written_capture_scope_mismatch");
  });

  it.each(["cancelled", "processing", "completed", "failed"])("does not capture a %s request", async status => {
    const main = harness({ canonical: { ...canonicalData, status } });
    expect((await main.inspect(currentJob, new AbortController().signal)).requested).toBe(false);
  });

  it("does not capture a later FIFO request while the canonical request differs", async () => {
    const main = harness({ canonical: { ...canonicalData, requestId: "synthetic-earlier-request" } });
    expect((await main.inspect(currentJob, new AbortController().signal)).requested).toBe(false);
  });

  it("does not recapture an old request rediscovered after reconnect or recent-ID rotation", async () => {
    vi.useFakeTimers();
    const serverNow = Date.parse("2026-11-01T05:00:00.000Z");
    vi.setSystemTime(serverNow - 3_600_000);
    const main = harness({
      canonical: { ...canonicalData, createdAtMs: serverNow - 60_000 },
      timestamp: new Date(serverNow).toISOString(),
    });
    expect((await main.inspect(currentJob, new AbortController().signal)).requested).toBe(false);
  });

  it("uses the server envelope clock to keep a fresh request valid when the local clock is ahead", async () => {
    vi.useFakeTimers();
    const serverNow = Date.parse("2026-11-01T05:00:00.000Z");
    vi.setSystemTime(serverNow + 28_800_000);
    const main = harness({
      canonical: { ...canonicalData, createdAtMs: serverNow - 15_000 },
      timestamp: new Date(serverNow).toISOString(),
    });
    expect(await main.inspect(currentJob, new AbortController().signal)).toEqual({ current: true, requested: true });
  });

  it.each([
    { bound: false }, { registered: false }, { sessionStatus: "ended" }, { sessionMode: "mock" },
    { binding: { ...binding, deviceId: "synthetic-other-device" } },
    { binding: { ...binding, manualCode: "synthetic-other-code" } },
    { binding: { ...binding, ownerUserId: undefined } },
    { binding: { ...binding, bindingId: "synthetic-other-binding" } },
  ])("requires the server to verify the current live written binding: %j", async mismatch => {
    const main = harness({ pairing: { ...pairingData, ...mismatch } });
    expect((await main.inspect(currentJob, new AbortController().signal)).requested).toBe(false);
    expect(main.fetch).toHaveBeenCalledTimes(1);
  });

  it("discards a pending-status response arriving after the local binding generation changes", async () => {
    const late = deferred<Response>();
    const main = harness({ fetch: async url => url.includes("pairing-status") ? response(pairingData) : late.promise });
    const inspecting = main.inspect(currentJob, new AbortController().signal);
    for (let index = 0; index < 8; index++) await Promise.resolve();
    main.setGeneration(3);
    late.resolve(response(canonicalData));
    const result = await inspecting;
    expect(result.current && result.requested).toBe(false);
  });

  it("discards pending-status results after cancellation even if the server ignored abort", async () => {
    const late = deferred<Response>();
    const main = harness({ fetch: async url => url.includes("pairing-status") ? response(pairingData) : late.promise });
    const controller = new AbortController();
    const inspecting = main.inspect(currentJob, controller.signal);
    for (let index = 0; index < 8; index++) await Promise.resolve();
    controller.abort();
    late.resolve(response(canonicalData));
    const result = await inspecting;
    expect(result.current && result.requested).toBe(false);
  });

  it("does not release a new session's power lease when an old recovery check rejects", async () => {
    const late = deferred<Response>();
    const main = harness({ fetch: () => late.promise });
    const context = { signal: new AbortController().signal, isCurrent: () => true };
    const recovery = main.recover(context);
    for (let index = 0; index < 8; index++) await Promise.resolve();
    main.setGeneration(3);
    main.setBindingKey("synthetic-new-session:synthetic-new-binding");
    late.reject(new Error("synthetic obsolete transport failure"));
    await recovery;
    expect(main.awake).not.toHaveBeenCalled();
    expect(main.restart).not.toHaveBeenCalled();
  });

  it("does not reopen delivery or release a current lease when the heartbeat context expires", async () => {
    const late = deferred<Response>();
    const main = harness({ fetch: () => late.promise });
    let current = true;
    const recovery = main.recover({ signal: new AbortController().signal, isCurrent: () => current });
    for (let index = 0; index < 8; index++) await Promise.resolve();
    current = false;
    late.reject(new Error("synthetic superseded heartbeat"));
    await recovery;
    expect(main.awake).not.toHaveBeenCalled();
    expect(main.restart).not.toHaveBeenCalled();
  });

  it("reopens suspended delivery only after verifying the same live written binding", async () => {
    const main = harness();
    await main.recover({ signal: new AbortController().signal, isCurrent: () => true });
    expect(main.awake).toHaveBeenCalledWith(true);
    expect(main.restart).toHaveBeenCalledOnce();
  });

  it("rejects an overdue recovery response before a delayed five-second timer runs", async () => {
    vi.useFakeTimers();
    const late = deferred<Response>();
    const main = harness({ fetch: () => late.promise });
    const recovery = main.recover({ signal: new AbortController().signal, isCurrent: () => true });
    for (let index = 0; index < 8; index++) await Promise.resolve();
    vi.setSystemTime(Date.now() + 5_001);
    late.resolve(response(pairingData));
    await recovery;
    expect(main.awake).not.toHaveBeenCalled();
    expect(main.restart).not.toHaveBeenCalled();
  });

  it("never re-enqueues the just-settled canonical request during its one pending probe", async () => {
    vi.useFakeTimers();
    const main = harness();
    main.probe(currentJob.requestId);
    main.probe(currentJob.requestId);
    await vi.advanceTimersByTimeAsync(0);
    expect(main.fetch).toHaveBeenCalledTimes(2);
    expect(main.process).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(60_000);
    expect(main.fetch).toHaveBeenCalledTimes(2);
    expect(vi.getTimerCount()).toBe(0);
  });

  it("admits one different current-session request discovered after explicit work", async () => {
    const main = harness({ canonical: { ...canonicalData, requestId: "synthetic-next-request" } });
    await main.poll(false, currentJob.requestId);
    expect(main.process).toHaveBeenCalledWith(identity, "synthetic-next-request", false);
  });

  it("does not open an event stream for an old run whose identity lookup resolves after stop", async () => {
    const identityLookup = deferred<{ live: boolean; identity: typeof identity }>();
    const main = loopHarness(() => identityLookup.promise);
    main.start();
    main.stop();
    identityLookup.resolve({ live: true, identity });
    for (let index = 0; index < 12; index++) await Promise.resolve();
    expect(main.consume).not.toHaveBeenCalled();
    expect(main.poll).not.toHaveBeenCalled();
  });

  it("does not let an old event-loop identity rejection launch a fallback after stop", async () => {
    const identityLookup = deferred<{ live: boolean; identity: typeof identity }>();
    const main = loopHarness(() => identityLookup.promise);
    main.start();
    main.stop();
    identityLookup.reject(new Error("synthetic stale identity failure"));
    for (let index = 0; index < 12; index++) await Promise.resolve();
    expect(main.consume).not.toHaveBeenCalled();
    expect(main.poll).not.toHaveBeenCalled();
  });

  it("does not let a hung old identity lookup block a later event-loop generation indefinitely", async () => {
    vi.useFakeTimers();
    const identityLookup = deferred<{ live: boolean; identity: typeof identity }>();
    const getState = vi.fn().mockImplementationOnce(() => identityLookup.promise)
      .mockResolvedValue({ live: true, identity });
    const main = loopHarness(getState);
    main.start();
    main.stop();
    main.start();
    await vi.advanceTimersByTimeAsync(8_001);
    expect(getState).toHaveBeenCalledTimes(2);
    expect(main.consume).toHaveBeenCalledOnce();
    main.stop();
  });

  it("does not clear the newer event-loop owner when an older identity lookup finally settles", async () => {
    const identityLookup = deferred<{ live: boolean; identity: typeof identity }>();
    const getState = vi.fn().mockImplementationOnce(() => identityLookup.promise)
      .mockResolvedValue({ live: true, identity });
    const main = loopHarness(getState);
    main.start();
    main.stop();
    main.start();
    for (let index = 0; index < 12; index++) await Promise.resolve();
    expect(main.owner()).toBe(main.generation());
    identityLookup.resolve({ live: true, identity });
    for (let index = 0; index < 12; index++) await Promise.resolve();
    expect(main.owner()).toBe(main.generation());
    expect(main.consume).toHaveBeenCalledOnce();
    main.stop();
  });
});
