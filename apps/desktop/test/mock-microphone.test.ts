import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { MockMicrophone } from "../src/renderer/audio/mock-microphone";

const fakes = vi.hoisted(() => ({ open: vi.fn(), processor: vi.fn(), resume: vi.fn() }));
vi.mock("../src/renderer/audio/audio-source-adapter", () => ({
  MicrophoneAudioAdapter: class { open = fakes.open; },
}));
vi.mock("../src/renderer/audio/realtime-publisher", () => ({
  createAudioCaptureProcessor: fakes.processor,
  downsampleToPcm16: () => new Uint8Array(3200),
}));

class Socket {
  static OPEN = 1;
  static instances: Socket[] = [];
  readyState = 1; bufferedAmount = 0;
  onopen = () => {}; onclose = () => {}; onmessage = (_: { data: string }) => {};
  send = vi.fn(); close = vi.fn(() => { this.readyState = 3; this.onclose(); });
  constructor(readonly url: URL) { Socket.instances.push(this); }
  capture(epoch: string | null) { this.onmessage({ data: JSON.stringify({ type: "capture", epoch }) }); }
}
let callbacks: ((samples: Float32Array) => void)[];
let tracks: { close: ReturnType<typeof vi.fn>; stream: object }[];
let contexts: { close: ReturnType<typeof vi.fn>; state: string }[];
let mic: MockMicrophone;
let states: ReturnType<typeof vi.fn<(state: "capturing" | "paused" | "error", message: string) => void>>;
let levels: ReturnType<typeof vi.fn<(level: number) => void>>;
let permission: ReturnType<typeof vi.fn<(granted: boolean) => void>>;
const settle = async () => { for (let i = 0; i < 12; i++) await Promise.resolve(); };

beforeEach(() => {
  vi.useFakeTimers(); vi.clearAllMocks(); Socket.instances = []; callbacks = []; tracks = []; contexts = [];
  vi.stubGlobal("WebSocket", Socket);
  vi.stubGlobal("AudioContext", class {
    state = "running"; sampleRate = 16000;
    close = vi.fn(async () => { this.state = "closed"; }); resume = fakes.resume;
    createMediaStreamSource = () => ({ connect: vi.fn(), disconnect: vi.fn() });
    constructor() { contexts.push(this); }
  });
  fakes.open.mockImplementation(async () => { const media = { close: vi.fn(), stream: {} }; tracks.push(media); return media; });
  fakes.resume.mockResolvedValue(undefined);
  fakes.processor.mockImplementation(async (_context, callback) => {
    callbacks.push(callback);
    return { detach: vi.fn(), processor: { disconnect: vi.fn() }, sink: { disconnect: vi.fn() } };
  });
  states = vi.fn();
  levels = vi.fn();
  permission = vi.fn();
  mic = new MockMicrophone({ apiBaseUrl: "https://synthetic.invalid/api/v1", sessionId: "mock-synthetic",
    deviceId: "synthetic-device", manualCode: "000000", microphoneId: "mic", onState: states, onLevel: levels, onPermission: permission });
  mic.start(); Socket.instances[0]!.onopen();
});
afterEach(async () => { await mic.stop(); vi.useRealTimers(); vi.unstubAllGlobals(); });

it("does not open a microphone before server grants a round; credentials are not in URL", async () => {
  const socket = Socket.instances[0]!;
  socket.capture(null); await settle();
  expect(fakes.open).not.toHaveBeenCalled();
  expect(levels).not.toHaveBeenCalled();
  expect(socket.url.toString()).toBe("wss://synthetic.invalid/api/v1/mock-interviews/mock-synthetic/microphone");
  expect(JSON.parse(socket.send.mock.calls[0]![0])).toEqual({ deviceId: "synthetic-device", manualCode: "000000" });
});

it("frames microphone audio with the current epoch and releases it on revocation", async () => {
  const socket = Socket.instances[0]!; const epoch = "a".repeat(32);
  socket.capture(epoch); await settle(); callbacks[0]!(new Float32Array(1600));
  const frame = socket.send.mock.lastCall![0] as Uint8Array;
  expect(frame.byteLength).toBe(3232);
  expect(new TextDecoder().decode(frame.slice(0, 32))).toBe(epoch);
  socket.capture(null); await settle();
  const count = socket.send.mock.calls.length; callbacks[0]!(new Float32Array(1600));
  expect(socket.send).toHaveBeenCalledTimes(count);
  expect(tracks[0]!.close).toHaveBeenCalledOnce(); expect(contexts[0]!.close).toHaveBeenCalledOnce();
});

it("drops old callbacks after a round change and closes on backpressure", async () => {
  const socket = Socket.instances[0]!;
  socket.capture("a".repeat(32)); await settle();
  socket.capture("b".repeat(32)); await settle();
  const count = socket.send.mock.calls.length; callbacks[0]!(new Float32Array(1600));
  expect(socket.send).toHaveBeenCalledTimes(count);
  callbacks[1]!(new Float32Array(1600));
  expect(new TextDecoder().decode(socket.send.mock.lastCall![0].slice(0, 32))).toBe("b".repeat(32));
  socket.bufferedAmount = 64001; callbacks[1]!(new Float32Array(1600)); await settle();
  expect(socket.close).toHaveBeenCalledOnce(); expect(tracks[1]!.close).toHaveBeenCalledOnce();
});

it("closes a microphone that finishes opening after stop and never reconnects", async () => {
  let resolve!: (value: unknown) => void;
  fakes.open.mockImplementationOnce(() => new Promise(done => { resolve = done; }));
  const socket = Socket.instances[0]!; socket.capture("a".repeat(32)); await settle();
  await mic.stop(); const close = vi.fn(); resolve({ close, stream: {} }); await settle();
  await vi.advanceTimersByTimeAsync(20000);
  expect(close).toHaveBeenCalledOnce(); expect(contexts).toHaveLength(0); expect(Socket.instances).toHaveLength(1);
});

it("retains the permission failure and does not reconnect or reopen denied microphone", async () => {
  fakes.open.mockRejectedValueOnce(new DOMException("synthetic-private-marker", "NotAllowedError"));
  const socket = Socket.instances[0]!;
  socket.capture("a".repeat(32)); await settle();
  await vi.advanceTimersByTimeAsync(60000);
  expect(states.mock.lastCall).toEqual(["error", "模拟面试麦克风权限被拒绝。请在系统设置中允许麦克风，然后点击“重试麦克风”。"]);
  expect(fakes.open).toHaveBeenCalledOnce();
  expect(permission).toHaveBeenLastCalledWith(false);
  expect(Socket.instances).toHaveLength(1);
  expect(socket.close).toHaveBeenCalledOnce();
  expect(socket.send.mock.calls).toHaveLength(1);
  expect(JSON.stringify(states.mock.calls)).not.toContain("synthetic-private-marker");
});

it("identifies a missing device without replacing its failure with paused state", async () => {
  fakes.open.mockRejectedValueOnce(new DOMException("synthetic", "NotFoundError"));
  Socket.instances[0]!.capture("a".repeat(32)); await settle();
  expect(states.mock.lastCall![0]).toBe("error");
  expect(states.mock.lastCall![1]).toContain("没有找到可用麦克风");
  expect(states.mock.calls.some(call => call[0] === "paused")).toBe(false);
});

it("ordinary network disconnection still reconnects and can capture with a fresh socket", async () => {
  Socket.instances[0]!.close(); await settle();
  await vi.advanceTimersByTimeAsync(1000);
  expect(Socket.instances).toHaveLength(2);
  Socket.instances[1]!.onopen();
  Socket.instances[1]!.capture("a".repeat(32)); await settle();
  expect(states.mock.lastCall![0]).toBe("capturing");
});

it("ignores a stale opening failure after the server has moved to another epoch", async () => {
  let reject!: (reason: unknown) => void;
  fakes.open.mockImplementationOnce(() => new Promise((_done, fail) => { reject = fail; }));
  const socket = Socket.instances[0]!;
  socket.capture("a".repeat(32)); await settle();
  socket.capture("b".repeat(32)); await settle();
  reject(new DOMException("synthetic", "NotAllowedError")); await settle();
  expect(states.mock.lastCall![0]).toBe("capturing");
  expect(socket.close).not.toHaveBeenCalled();
});

it("releases acquired media if audio processor startup fails", async () => {
  fakes.processor.mockRejectedValueOnce(new Error("synthetic-startup-marker"));
  Socket.instances[0]!.capture("a".repeat(32)); await settle();
  expect(tracks[0]!.close).toHaveBeenCalledOnce();
  expect(contexts[0]!.close).toHaveBeenCalledOnce();
  expect(states.mock.lastCall![0]).toBe("error");
  expect(JSON.stringify(states.mock.calls)).not.toContain("synthetic-startup-marker");
});

it("reports level only from active PCM callbacks and never from an old or paused capture", async () => {
  const socket = Socket.instances[0]!;
  socket.capture("a".repeat(32)); await settle();
  expect(levels).not.toHaveBeenCalled();
  expect(permission).toHaveBeenLastCalledWith(true);
  callbacks[0]!(new Float32Array(1600).fill(0.1));
  expect(levels).toHaveBeenCalledOnce();
  expect(levels.mock.lastCall![0]).toBeCloseTo(0.1);
  callbacks[0]!(new Float32Array(1600).fill(0.1));
  expect(levels).toHaveBeenCalledOnce();
  socket.capture(null); await settle();
  await vi.advanceTimersByTimeAsync(200);
  callbacks[0]!(new Float32Array(1600).fill(0.1));
  expect(levels).toHaveBeenCalledOnce();
});

it("releases media once when stopped during an in-flight audio context resume", async () => {
  let reject!: (reason: unknown) => void;
  fakes.resume.mockImplementationOnce(() => new Promise((_done, fail) => { reject = fail; }));
  Socket.instances[0]!.capture("a".repeat(32)); await settle();
  await mic.stop();
  reject(new Error("synthetic-stopped-context")); await settle();
  expect(tracks[0]!.close).toHaveBeenCalledOnce();
  expect(contexts[0]!.close).toHaveBeenCalledOnce();
  expect(states.mock.calls.some(call => call[0] === "error")).toBe(false);
});
