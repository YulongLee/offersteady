import { afterEach, describe, expect, it, vi } from "vitest";

import { BoundedAudioFrameBuffer, SourceFrameSequencer, createAudioFrame } from "../src/renderer/audio/audio-frame-buffer";
import { MultiplexedRealtimeTransport } from "../src/renderer/audio/multiplexed-realtime-transport";
import { RealtimeTransportDiagnostics } from "../src/renderer/audio/realtime-transport-diagnostics";


class FakeWebSocket {
  static readonly OPEN = 1;
  static instances: FakeWebSocket[] = [];
  readyState = 0;
  sent: Array<string | ArrayBuffer> = [];
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

  send(payload: string | ArrayBuffer) { this.sent.push(payload); }
  close(code = 1000) { this.readyState = 3; this.onclose?.({ code }); }
  serverEvent(payload: object) { this.onmessage?.({ data: JSON.stringify(payload) }); }
}

const decodeEnvelope = (payload: string | ArrayBuffer) => {
  expect(payload).toBeInstanceOf(ArrayBuffer);
  const bytes = new Uint8Array(payload as ArrayBuffer);
  const headerLength = new DataView(bytes.buffer).getUint32(0, false);
  return JSON.parse(new TextDecoder().decode(bytes.slice(4, 4 + headerLength))) as Record<string, unknown>;
};


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
    expect(FakeWebSocket.instances[0]!.url).toContain("media=binary-v1");
    expect(FakeWebSocket.instances[0]!.sent.map(item => decodeEnvelope(item).sourceKind)).toEqual(["microphone", "system"]);
    FakeWebSocket.instances[0]!.serverEvent({ kind: "sequence-gap", payload: { sourceKind: "microphone", expected: 0, received: 2 } });
    expect(events).toContainEqual({ kind: "sequence-gap", payload: { sourceKind: "microphone", expected: 0, received: 2 } });
    transport.stop();
  });

  it("observes a sequence-gap resend at the actual websocket boundary", async () => {
    vi.stubGlobal("window", {
      location: { href: "https://mianshiwen.cc/interviews/session" },
      setTimeout,
      clearTimeout,
      setInterval,
      clearInterval,
    });
    vi.stubGlobal("WebSocket", FakeWebSocket);
    const diagnostics = new RealtimeTransportDiagnostics("trace-session", () => undefined, 10_000, 0);
    const transport = new MultiplexedRealtimeTransport({
      apiBaseUrl: "https://mianshiwen.cc/api/v1",
      token: "trace-token",
      diagnostics,
      onEvent: () => undefined,
      onState: () => undefined,
    });
    await transport.start();
    transport.enqueue({
      sourceKind: "system",
      sourceId: "loopback",
      sequence: 12,
      codec: "pcm-s16le",
      sampleRateHz: 16_000,
      channels: 1,
      audioBase64: btoa("abcd"),
    });
    FakeWebSocket.instances[0]!.serverEvent({ kind: "sequence-gap", payload: { sourceKind: "system", expected: 12, received: 13 } });
    FakeWebSocket.instances[0]!.serverEvent({ kind: "frame-accepted", payload: { sourceKind: "system", sourceId: "loopback", sequence: 12 } });

    expect(FakeWebSocket.instances[0]!.sent).toHaveLength(2);
    expect(diagnostics.publish(10_000).SYSTEM).toMatchObject({
      unique_frames: 1,
      websocket_send_calls: 2,
      ack_count: 1,
      resend_frames: 1,
      sequence_gap_count: 1,
      sequence_gap_recovery_frames: 1,
      retransmit_queue_depth: 0,
      send_amplification_ratio: 2,
      byte_amplification_ratio: 2,
    });
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

  it("keeps a terminal until its explicit acknowledgement and does not enqueue it twice", async () => {
    vi.stubGlobal("window", { location: { href: "https://mianshiwen.cc/interviews/session" }, setTimeout, clearTimeout });
    vi.stubGlobal("WebSocket", FakeWebSocket);
    const transport = new MultiplexedRealtimeTransport({
      apiBaseUrl: "https://mianshiwen.cc/api/v1",
      token: "terminal-token",
      onEvent: () => undefined,
      onState: () => undefined,
    });
    await transport.start();
    const terminal = { sourceKind: "system", sourceId: "loopback", sequence: 9, isFinal: true, terminalId: "terminal-9", capturedAtMs: Date.now() };
    transport.enqueue(terminal);
    transport.enqueue(terminal);
    expect(transport.pendingPayloads()).toHaveLength(1);
    FakeWebSocket.instances[0]!.serverEvent({ kind: "terminal-accepted", payload: { ...terminal, acceptedAtMs: Date.now() } });
    expect(transport.pendingPayloads()).toHaveLength(0);
    transport.stop();
  });

  it("keeps final boundaries when the recovery queue overflows", async () => {
    vi.stubGlobal("window", { location: { href: "https://mianshiwen.cc/interviews/session" }, setTimeout, clearTimeout });
    vi.stubGlobal("WebSocket", FakeWebSocket);
    const events: Array<{ kind?: string; payload?: Record<string, unknown> }> = [];
    const transport = new MultiplexedRealtimeTransport({
      apiBaseUrl: "https://mianshiwen.cc/api/v1",
      token: "bounded-token",
      onEvent: event => events.push(event),
      onState: () => undefined,
    });
    await transport.start();
    transport.enqueue({ sourceKind: "microphone", sourceId: "mic", sequence: 0, isFinal: true, capturedAtMs: Date.now() });
    for (let sequence = 1; sequence <= 256; sequence += 1) {
      transport.enqueue({ sourceKind: "microphone", sourceId: "mic", sequence, isFinal: false, capturedAtMs: Date.now() });
    }
    const pending = transport.pendingPayloads();
    expect(pending.some(item => item.sequence === 0 && item.isFinal === true)).toBe(true);
    expect(pending.some(item => item.sequence === 1)).toBe(false);
    expect(events).toContainEqual(expect.objectContaining({
      kind: "sequence-gap",
      payload: expect.objectContaining({ reason: "desktop-buffer-overflow", sequence: 1, droppedFrames: 1 }),
    }));
    transport.stop();
  });

  it("hands unacknowledged frames to the credential refresh callback", async () => {
    vi.stubGlobal("window", { location: { href: "https://mianshiwen.cc/interviews/session" }, setTimeout, clearTimeout });
    vi.stubGlobal("WebSocket", FakeWebSocket);
    const terminals: Array<{ code: number; reason: string; pending: readonly Record<string, unknown>[] }> = [];
    const transport = new MultiplexedRealtimeTransport({
      apiBaseUrl: "https://mianshiwen.cc/api/v1",
      token: "expired-token",
      onEvent: () => undefined,
      onState: () => undefined,
      onTerminal: terminal => terminals.push(terminal),
    });
    await transport.start();
    transport.enqueue({ sourceKind: "system", sourceId: "loopback", sequence: 0, isFinal: false, capturedAtMs: Date.now() });
    FakeWebSocket.instances[0]!.close(1008);
    expect(terminals).toHaveLength(1);
    expect(terminals[0]).toMatchObject({ code: 1008, reason: "publisher-credential-rejected" });
    expect(terminals[0]?.pending).toHaveLength(1);
  });
});
