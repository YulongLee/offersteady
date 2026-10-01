import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { MockMicrophone } from "../src/renderer/audio/mock-microphone";

const fakes = vi.hoisted(() => ({ open: vi.fn(), processor: vi.fn() }));
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
const settle = async () => { for (let i = 0; i < 12; i++) await Promise.resolve(); };

beforeEach(() => {
  vi.useFakeTimers(); vi.clearAllMocks(); Socket.instances = []; callbacks = []; tracks = []; contexts = [];
  vi.stubGlobal("WebSocket", Socket);
  vi.stubGlobal("AudioContext", class {
    state = "running"; sampleRate = 16000;
    close = vi.fn(async () => { this.state = "closed"; }); resume = vi.fn(async () => {});
    createMediaStreamSource = () => ({ connect: vi.fn(), disconnect: vi.fn() });
    constructor() { contexts.push(this); }
  });
  fakes.open.mockImplementation(async () => { const media = { close: vi.fn(), stream: {} }; tracks.push(media); return media; });
  fakes.processor.mockImplementation(async (_context, callback) => {
    callbacks.push(callback);
    return { detach: vi.fn(), processor: { disconnect: vi.fn() }, sink: { disconnect: vi.fn() } };
  });
  mic = new MockMicrophone({ apiBaseUrl: "https://synthetic.invalid/api/v1", sessionId: "mock-synthetic",
    deviceId: "synthetic-device", manualCode: "000000", microphoneId: "mic", onState: vi.fn() });
  mic.start(); Socket.instances[0]!.onopen();
});
afterEach(async () => { await mic.stop(); vi.useRealTimers(); vi.unstubAllGlobals(); });

it("does not open a microphone before server grants a round; credentials are not in URL", async () => {
  const socket = Socket.instances[0]!;
  socket.capture(null); await settle();
  expect(fakes.open).not.toHaveBeenCalled();
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
