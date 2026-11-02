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
class Track extends EventTarget {
  readyState = "live";
  muted = false;
  end() { this.readyState = "ended"; this.dispatchEvent(new Event("ended")); }
  mute() { this.muted = true; this.dispatchEvent(new Event("mute")); }
  unmute() { this.muted = false; this.dispatchEvent(new Event("unmute")); }
}
class Context extends EventTarget {
  state = "running"; sampleRate = 16000;
  close = vi.fn(async () => { this.state = "closed"; this.dispatchEvent(new Event("statechange")); });
  resume = fakes.resume;
  createMediaStreamSource = () => ({ connect: vi.fn(), disconnect: vi.fn() });
  constructor() { super(); contexts.push(this); }
  change(state: string) { this.state = state; this.dispatchEvent(new Event("statechange")); }
}
let tracks: { close: ReturnType<typeof vi.fn>; stream: { getAudioTracks: () => Track[] }; track: Track }[];
let contexts: Context[];
let mic: MockMicrophone;
let states: ReturnType<typeof vi.fn<(state: "capturing" | "paused" | "error", message: string) => void>>;
let levels: ReturnType<typeof vi.fn<(level: number) => void>>;
let permission: ReturnType<typeof vi.fn<(granted: boolean) => void>>;
const settle = async () => { for (let i = 0; i < 12; i++) await Promise.resolve(); };

beforeEach(() => {
  vi.useFakeTimers(); vi.clearAllMocks(); Socket.instances = []; callbacks = []; tracks = []; contexts = [];
  vi.stubGlobal("WebSocket", Socket);
  vi.stubGlobal("AudioContext", Context);
  fakes.open.mockImplementation(async () => {
    const track = new Track();
    const media = { close: vi.fn(() => track.end()), stream: { getAudioTracks: () => [track] }, track };
    tracks.push(media); return media;
  });
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

it("does not claim capture when resume resolves without a running context", async () => {
  fakes.resume.mockImplementationOnce(async () => { contexts[0]!.state = "suspended"; });
  const socket = Socket.instances[0]!;
  socket.capture("a".repeat(32)); await settle();
  expect(states.mock.calls.some(call => call[0] === "capturing")).toBe(false);
  expect(states.mock.lastCall).toEqual(["error", "模拟面试收音已中断。请点击“重试麦克风”恢复。"]);
  expect(permission.mock.calls).toEqual([[true]]);
  expect(tracks[0]!.close).toHaveBeenCalledOnce();
  expect(contexts[0]!.close).toHaveBeenCalledOnce();
  callbacks[0]!(new Float32Array(1600));
  await vi.advanceTimersByTimeAsync(20000);
  expect(Socket.instances).toHaveLength(1);
  expect(socket.send).toHaveBeenCalledOnce();
});

it("does not turn an AudioContext NotAllowedError into microphone denial", async () => {
  fakes.resume.mockRejectedValueOnce(new DOMException("synthetic-private-context", "NotAllowedError"));
  Socket.instances[0]!.capture("a".repeat(32)); await settle();
  expect(permission.mock.calls).toEqual([[true]]);
  expect(states.mock.lastCall![1]).toContain("收音已中断");
  expect(JSON.stringify(states.mock.calls)).not.toContain("synthetic-private-context");
  expect(tracks[0]!.close).toHaveBeenCalledOnce();
});

it("keeps constructor and processor security failures separate from microphone authorization", async () => {
  fakes.processor.mockRejectedValueOnce(new DOMException("synthetic-processor-security", "SecurityError"));
  Socket.instances[0]!.capture("a".repeat(32)); await settle();
  expect(permission.mock.calls).toEqual([[true]]);
  expect(states.mock.lastCall![1]).toContain("收音已中断");
  expect(states.mock.lastCall![1]).not.toContain("权限被拒绝");
  expect(tracks[0]!.close).toHaveBeenCalledOnce();
});

it("releases acquired media when the audio context constructor is rejected", async () => {
  vi.stubGlobal("AudioContext", class {
    constructor() { throw new DOMException("synthetic-context-creation", "NotAllowedError"); }
  });
  Socket.instances[0]!.capture("a".repeat(32)); await settle();
  expect(permission.mock.calls).toEqual([[true]]);
  expect(states.mock.lastCall![1]).toContain("收音已中断");
  expect(tracks[0]!.close).toHaveBeenCalledOnce();
});

it("bounds a stalled resume and releases input without reconnecting", async () => {
  let resolve!: () => void;
  fakes.resume.mockImplementationOnce(() => new Promise<void>(done => { resolve = done; }));
  const socket = Socket.instances[0]!;
  socket.capture("a".repeat(32)); await settle();
  callbacks[0]!(new Float32Array(1600));
  await vi.advanceTimersByTimeAsync(2999);
  expect(states.mock.calls.some(call => call[0] === "capturing" || call[0] === "error")).toBe(false);
  expect(socket.send).toHaveBeenCalledOnce();
  await vi.advanceTimersByTimeAsync(1); await settle();
  expect(states.mock.lastCall![0]).toBe("error");
  expect(tracks[0]!.close).toHaveBeenCalledOnce();
  resolve(); await settle();
  await vi.advanceTimersByTimeAsync(20000);
  expect(states.mock.calls.some(call => call[0] === "capturing")).toBe(false);
  expect(permission.mock.calls).toEqual([[true]]);
  expect(Socket.instances).toHaveLength(1);
});

it("can resume within the bound and never uploads PCM produced before capture is ready", async () => {
  let resolve!: () => void;
  fakes.resume.mockImplementationOnce(() => {
    contexts[0]!.change("suspended");
    return new Promise<void>(done => { resolve = done; });
  });
  const socket = Socket.instances[0]!;
  socket.capture("a".repeat(32)); await settle();
  callbacks[0]!(new Float32Array(1600));
  await vi.advanceTimersByTimeAsync(1000);
  expect(states.mock.calls.some(call => call[0] === "error")).toBe(false);
  expect(socket.send).toHaveBeenCalledOnce();
  contexts[0]!.change("running"); resolve(); await settle();
  expect(states.mock.lastCall![0]).toBe("capturing");
  callbacks[0]!(new Float32Array(1600));
  expect(socket.send).toHaveBeenCalledTimes(2);
  expect((socket.send.mock.lastCall![0] as Uint8Array).byteLength).toBe(3232);
});

it.each(["suspended", "interrupted", "closed"])("fences input when the active audio context becomes %s", async state => {
  const socket = Socket.instances[0]!;
  socket.capture("a".repeat(32)); await settle();
  const previous = states.mock.calls.length;
  contexts[0]!.change(state); await settle();
  expect(states.mock.calls.slice(previous)).toEqual([["error", "模拟面试收音已中断。请点击“重试麦克风”恢复。"]]);
  expect(tracks[0]!.close).toHaveBeenCalledOnce();
  const sent = socket.send.mock.calls.length;
  callbacks[0]!(new Float32Array(1600));
  contexts[0]!.change("running");
  await vi.advanceTimersByTimeAsync(20000);
  expect(socket.send).toHaveBeenCalledTimes(sent);
  expect(Socket.instances).toHaveLength(1);
  expect(permission.mock.calls).toEqual([[true]]);
});

it("detects ended input even when the selected device id has not changed", async () => {
  const socket = Socket.instances[0]!;
  socket.capture("a".repeat(32)); await settle();
  tracks[0]!.track.end(); await settle();
  expect(states.mock.lastCall![0]).toBe("error");
  expect(states.mock.lastCall![1]).toContain("麦克风已断开");
  expect(tracks[0]!.close).toHaveBeenCalledOnce();
  expect(contexts[0]!.close).toHaveBeenCalledOnce();
  const sent = socket.send.mock.calls.length;
  callbacks[0]!(new Float32Array(1600));
  await vi.advanceTimersByTimeAsync(20000);
  expect(socket.send).toHaveBeenCalledTimes(sent);
  expect(Socket.instances).toHaveLength(1);
  expect(permission.mock.calls).toEqual([[true]]);
});

it("allows a brief input mute to recover but fails a persistent mute within the same round", async () => {
  Socket.instances[0]!.capture("a".repeat(32)); await settle();
  tracks[0]!.track.mute();
  await vi.advanceTimersByTimeAsync(1000);
  tracks[0]!.track.unmute();
  await vi.advanceTimersByTimeAsync(1000);
  expect(states.mock.calls.some(call => call[0] === "error")).toBe(false);
  expect(tracks[0]!.close).not.toHaveBeenCalled();
  tracks[0]!.track.mute();
  await vi.advanceTimersByTimeAsync(1000);
  tracks[0]!.track.dispatchEvent(new Event("mute"));
  await vi.advanceTimersByTimeAsync(500);
  expect(states.mock.lastCall![0]).toBe("error");
  expect(states.mock.lastCall![1]).toContain("暂时无法提供声音");
  expect(tracks[0]!.close).toHaveBeenCalledOnce();
  expect(permission.mock.calls).toEqual([[true]]);
});

it("does not interpret silent PCM as permission failure or a muted device", async () => {
  const socket = Socket.instances[0]!;
  socket.capture("a".repeat(32)); await settle();
  callbacks[0]!(new Float32Array(1600));
  await vi.advanceTimersByTimeAsync(3000);
  callbacks[0]!(new Float32Array(1600));
  expect(states.mock.lastCall![0]).toBe("capturing");
  expect(states.mock.calls.some(call => call[0] === "error")).toBe(false);
  expect(permission.mock.calls).toEqual([[true]]);
  expect(tracks[0]!.close).not.toHaveBeenCalled();
});

it("discards ended, mute, context and PCM callbacks belonging to a replaced round", async () => {
  const socket = Socket.instances[0]!;
  socket.capture("a".repeat(32)); await settle();
  tracks[0]!.track.mute();
  socket.capture("b".repeat(32)); await settle();
  const stateCount = states.mock.calls.length;
  tracks[0]!.track.end(); tracks[0]!.track.mute(); contexts[0]!.change("suspended");
  callbacks[0]!(new Float32Array(1600));
  await vi.advanceTimersByTimeAsync(2000);
  expect(states).toHaveBeenCalledTimes(stateCount);
  expect(tracks[1]!.close).not.toHaveBeenCalled();
  callbacks[1]!(new Float32Array(1600));
  expect(new TextDecoder().decode(socket.send.mock.lastCall![0].slice(0, 32))).toBe("b".repeat(32));
});

it("cancels pending mute and resume work as soon as the server pauses capture", async () => {
  let resolve!: () => void;
  fakes.resume.mockImplementationOnce(() => new Promise<void>(done => { resolve = done; }));
  const socket = Socket.instances[0]!;
  socket.capture("a".repeat(32)); await settle();
  tracks[0]!.track.mute();
  socket.capture(null); await settle();
  await vi.advanceTimersByTimeAsync(10000);
  resolve(); await settle();
  expect(states.mock.lastCall![0]).toBe("paused");
  expect(states.mock.calls.some(call => call[0] === "error" || call[0] === "capturing")).toBe(false);
  expect(tracks[0]!.close).toHaveBeenCalledOnce();
  expect(socket.close).not.toHaveBeenCalled();
});

it("does not accept a stale denied open after A to B to A replacement", async () => {
  let reject!: (reason: unknown) => void;
  fakes.open.mockImplementationOnce(() => new Promise((_done, fail) => { reject = fail; }));
  const socket = Socket.instances[0]!;
  socket.capture("a".repeat(32)); await settle();
  socket.capture("b".repeat(32)); await settle();
  socket.capture("a".repeat(32)); await settle();
  const stateCount = states.mock.calls.length;
  reject(new DOMException("synthetic-stale-denied", "NotAllowedError")); await settle();
  expect(states).toHaveBeenCalledTimes(stateCount);
  expect(permission.mock.calls).toEqual([[true], [true]]);
  expect(socket.close).not.toHaveBeenCalled();
  expect(tracks[1]!.close).not.toHaveBeenCalled();
});

it("does not let a late old resume failure close the replacement capture", async () => {
  let reject!: (reason: unknown) => void;
  fakes.resume.mockImplementationOnce(() => new Promise((_done, fail) => { reject = fail; }));
  const socket = Socket.instances[0]!;
  socket.capture("a".repeat(32)); await settle();
  socket.capture("b".repeat(32)); await settle();
  const stateCount = states.mock.calls.length;
  reject(new DOMException("synthetic-old-resume", "NotAllowedError")); await settle();
  expect(states).toHaveBeenCalledTimes(stateCount);
  expect(states.mock.lastCall![0]).toBe("capturing");
  expect(tracks[1]!.close).not.toHaveBeenCalled();
  expect(socket.close).not.toHaveBeenCalled();
  expect(permission.mock.calls).toEqual([[true], [true]]);
});

it("releases input while processor creation is pending and detaches the late processor", async () => {
  let resolve!: (processor: unknown) => void;
  fakes.processor.mockImplementationOnce(() => new Promise(done => { resolve = done; }));
  Socket.instances[0]!.capture("a".repeat(32)); await settle();
  await mic.stop();
  expect(tracks[0]!.close).toHaveBeenCalledOnce();
  expect(contexts[0]!.close).toHaveBeenCalledOnce();
  const late = { detach: vi.fn(), processor: { disconnect: vi.fn() }, sink: { disconnect: vi.fn() } };
  resolve(late); await settle();
  expect(late.detach).toHaveBeenCalledOnce();
  expect(late.processor.disconnect).toHaveBeenCalledOnce();
  expect(late.sink.disconnect).toHaveBeenCalledOnce();
  expect(states.mock.calls.some(call => call[0] === "capturing" || call[0] === "error")).toBe(false);
});

it("bounds a stalled AudioContext close without keeping the microphone or old round alive", async () => {
  const socket = Socket.instances[0]!;
  socket.capture("a".repeat(32)); await settle();
  contexts[0]!.close.mockImplementationOnce(() => new Promise<void>(() => {}));
  socket.capture("b".repeat(32)); await settle();
  expect(tracks[0]!.close).toHaveBeenCalledOnce();
  expect(tracks).toHaveLength(1);
  const sent = socket.send.mock.calls.length;
  callbacks[0]!(new Float32Array(1600));
  expect(socket.send).toHaveBeenCalledTimes(sent);
  await vi.advanceTimersByTimeAsync(1000); await settle();
  expect(tracks).toHaveLength(2);
  expect(states.mock.lastCall![0]).toBe("capturing");
});

it("does not create duplicate connections or heartbeats on repeated start or late socket open", async () => {
  const old = Socket.instances[0]!;
  mic.start(); old.onopen();
  expect(Socket.instances).toHaveLength(1);
  old.close(); await settle();
  await vi.advanceTimersByTimeAsync(1000);
  const next = Socket.instances[1]!; next.onopen();
  const previous = old.send.mock.calls.length;
  old.onopen(); old.onclose();
  await vi.advanceTimersByTimeAsync(10000);
  expect(old.send).toHaveBeenCalledTimes(previous);
  expect(next.send).toHaveBeenCalledTimes(3);
  expect(Socket.instances).toHaveLength(2);
});

it("reconnects after a network loss with new input while old input callbacks remain fenced", async () => {
  const old = Socket.instances[0]!;
  old.capture("a".repeat(32)); await settle();
  old.close(); await settle();
  await vi.advanceTimersByTimeAsync(1000);
  const next = Socket.instances[1]!; next.onopen(); next.capture("a".repeat(32)); await settle();
  const count = next.send.mock.calls.length;
  callbacks[0]!(new Float32Array(1600)); tracks[0]!.track.end(); contexts[0]!.change("suspended");
  expect(next.send).toHaveBeenCalledTimes(count);
  expect(tracks[1]!.close).not.toHaveBeenCalled();
  callbacks[1]!(new Float32Array(1600));
  expect(next.send).toHaveBeenCalledTimes(count + 1);
  expect(states.mock.lastCall![0]).toBe("capturing");
});

it("does not upload after a level callback synchronously stops the current microphone", async () => {
  const socket = Socket.instances[0]!;
  socket.capture("a".repeat(32)); await settle();
  levels.mockImplementationOnce(() => { void mic.stop(); });
  callbacks[0]!(new Float32Array(1600)); await settle();
  expect(levels).toHaveBeenCalledOnce();
  expect(socket.send).toHaveBeenCalledOnce();
  expect(tracks[0]!.close).toHaveBeenCalledOnce();
});
