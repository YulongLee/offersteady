import { afterEach, describe, expect, it, vi } from "vitest";

import { BoundedAudioFrameBuffer, SourceFrameSequencer, createAudioFrame } from "../src/renderer/audio/audio-frame-buffer";
import { MultiplexedRealtimeTransport } from "../src/renderer/audio/multiplexed-realtime-transport";


class FakeWebSocket {
  static readonly OPEN = 1;
  static instances: FakeWebSocket[] = [];
  readyState = 0;
  sent: string[] = [];
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: (() => void) | null = null;
  onclose: ((event: { code: number }) => void) | null = null;

  constructor(readonly url: string) {
    FakeWebSocket.instances.push(this);
    queueMicrotask(() => {
      this.readyState = FakeWebSocket.OPEN;
      this.onopen?.();
    });
  }

  send(payload: string) { this.sent.push(payload); }
  close(code = 1000) { this.readyState = 3; this.onclose?.({ code }); }
  serverEvent(payload: object) { this.onmessage?.({ data: JSON.stringify(payload) }); }
}


describe("realtime transport v2", () => {
  afterEach(() => {
    FakeWebSocket.instances = [];
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("multiplexes both role channels through one bounded websocket", async () => {
    vi.stubGlobal("window", {
      location: { href: "https://mianshiwen.cc/interviews/session" },
      setTimeout,
      clearTimeout,
    });
    vi.stubGlobal("WebSocket", FakeWebSocket);
    const events: unknown[] = [];
    const transport = new MultiplexedRealtimeTransport({
      apiBaseUrl: "https://mianshiwen.cc/api/v1",
      token: "synthetic-token",
      onEvent: event => events.push(event),
      onState: () => undefined,
    });
    await transport.start();
    transport.enqueue({ sourceKind: "microphone", sourceId: "mic", sequence: 0, isFinal: false });
    transport.enqueue({ sourceKind: "system", sourceId: "system", sequence: 0, isFinal: false });
    expect(FakeWebSocket.instances).toHaveLength(1);
    expect(FakeWebSocket.instances[0]!.url).toContain("protocol=2.0");
    expect(FakeWebSocket.instances[0]!.sent.map(item => JSON.parse(item).sourceKind)).toEqual(["microphone", "system"]);
    FakeWebSocket.instances[0]!.serverEvent({ kind: "sequence-gap", payload: { sourceKind: "microphone", expected: 0, received: 2 } });
    expect(events).toContainEqual({ kind: "sequence-gap", payload: { sourceKind: "microphone", expected: 0, received: 2 } });
    transport.stop();
  });

  it("keeps approximately two seconds of pcm and sequences by logical channel", () => {
    const sequencer = new SourceFrameSequencer();
    const buffer = new BoundedAudioFrameBuffer(64_000);
    const first = createAudioFrame(sequencer, { sessionId: "s", deviceId: "d", sourceId: "airpods", sourceKind: "microphone", capturedAtMs: 1, durationMs: 1000, payload: new Uint8Array(32_000) });
    const second = createAudioFrame(sequencer, { sessionId: "s", deviceId: "d", sourceId: "mac-mic", sourceKind: "microphone", capturedAtMs: 2, durationMs: 1000, payload: new Uint8Array(32_000) });
    const third = createAudioFrame(sequencer, { sessionId: "s", deviceId: "d", sourceId: "usb-mic", sourceKind: "microphone", capturedAtMs: 3, durationMs: 1000, payload: new Uint8Array(32_000) });
    expect([first.sequence, second.sequence, third.sequence]).toEqual([0, 1, 2]);
    buffer.push(first);
    buffer.push(second);
    expect(buffer.push(third)).toEqual([first]);
  });

  it("reconnects once and reuses unacknowledged frames", async () => {
    vi.useFakeTimers();
    vi.stubGlobal("window", {
      location: { href: "https://mianshiwen.cc/interviews/session" },
      setTimeout,
      clearTimeout,
    });
    vi.stubGlobal("WebSocket", FakeWebSocket);
    const transport = new MultiplexedRealtimeTransport({
      apiBaseUrl: "https://mianshiwen.cc/api/v1",
      token: "resume-token",
      onEvent: () => undefined,
      onState: () => undefined,
    });
    const started = transport.start();
    await vi.runAllTicks();
    await started;
    transport.enqueue({ sourceKind: "microphone", sourceId: "mic", sequence: 0, isFinal: true });
    FakeWebSocket.instances[0]!.close(1006);
    await vi.advanceTimersByTimeAsync(5500);
    expect(FakeWebSocket.instances).toHaveLength(2);
    expect(FakeWebSocket.instances[1]!.sent).toHaveLength(1);
    transport.stop();
  });
});
