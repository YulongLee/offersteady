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

const acceptConnection = (socket: FakeWebSocket, microphone = -1, system = -1) => {
  socket.serverEvent({ kind: "connection-state", payload: { resumeOffsets: { microphone, system } } });
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
    acceptConnection(FakeWebSocket.instances[0]!);
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
    acceptConnection(FakeWebSocket.instances[0]!, -1, 11);
    transport.enqueue({
      sourceKind: "system",
      sourceId: "loopback",
      sequence: 12,
      codec: "pcm-s16le",
      sampleRateHz: 16_000,
      channels: 1,
      audioBase64: btoa("abcd"),
    });
    expect(FakeWebSocket.instances[0]!.sent).toHaveLength(1);
    FakeWebSocket.instances[0]!.serverEvent({ kind: "sequence-gap", payload: { sourceKind: "system", expected: 12, received: 13 } });
    for (let index = 0; index < 100; index += 1) {
      FakeWebSocket.instances[0]!.serverEvent({ kind: "sequence-gap", payload: { sourceKind: "system", expected: 12, received: 13 } });
    }
    FakeWebSocket.instances[0]!.serverEvent({ kind: "frame-accepted", payload: { sourceKind: "system", sourceId: "loopback", sequence: 12 } });

    expect(FakeWebSocket.instances[0]!.sent).toHaveLength(2);
    expect(diagnostics.publish(10_000).SYSTEM).toMatchObject({
      unique_frames: 1,
      websocket_send_calls: 2,
      ack_count: 1,
      resend_frames: 1,
      sequence_gap_count: 101,
      sequence_gap_recovery_frames: 1,
      retransmit_queue_depth: 0,
      send_amplification_ratio: 2,
      byte_amplification_ratio: 2,
    });
    transport.stop();
  });

  it("does not reopen the entire in-flight channel window for duplicate gaps inside cooldown", async () => {
    vi.useFakeTimers();
    vi.setSystemTime(1_000);
    vi.stubGlobal("window", {
      location: { href: "https://mianshiwen.cc/interviews/session" },
      setTimeout,
      clearTimeout,
    });
    vi.stubGlobal("WebSocket", FakeWebSocket);
    const transport = new MultiplexedRealtimeTransport({
      apiBaseUrl: "https://mianshiwen.cc/api/v1",
      token: "duplicate-gap-token",
      onEvent: () => undefined,
      onState: () => undefined,
    });
    await transport.start();
    acceptConnection(FakeWebSocket.instances[0]!, -1, -1);
    for (let sequence = 0; sequence < 8; sequence += 1) {
      transport.enqueue({ sourceKind: "system", sourceId: "loopback", sequence, isFinal: false });
    }
    expect(FakeWebSocket.instances[0]!.sent).toHaveLength(8);
    FakeWebSocket.instances[0]!.serverEvent({ kind: "sequence-gap", payload: { sourceKind: "system", expected: 0, received: 8 } });
    expect(FakeWebSocket.instances[0]!.sent).toHaveLength(9);
    FakeWebSocket.instances[0]!.serverEvent({ kind: "sequence-gap", payload: { sourceKind: "system", expected: 0, received: 8 } });
    transport.enqueue({ sourceKind: "system", sourceId: "loopback", sequence: 8, isFinal: false });
    expect(FakeWebSocket.instances[0]!.sent).toHaveLength(9);
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
    acceptConnection(FakeWebSocket.instances[0]!);
    transport.enqueue({ sourceKind: "microphone", sourceId: "mic", sequence: 0, isFinal: true });
    FakeWebSocket.instances[0]!.close(1006);
    await vi.advanceTimersByTimeAsync(5500);
    expect(FakeWebSocket.instances).toHaveLength(2);
    acceptConnection(FakeWebSocket.instances[1]!);
    expect(FakeWebSocket.instances[1]!.sent).toHaveLength(1);
    transport.stop();
  });

  it("reconnects an unexpected clean close and ignores stale socket events", async () => {
    vi.useFakeTimers();
    vi.stubGlobal("window", { location: { href: "https://mianshiwen.cc/interviews/session" }, setTimeout, clearTimeout });
    vi.stubGlobal("WebSocket", FakeWebSocket);
    const states: string[] = [];
    const transport = new MultiplexedRealtimeTransport({
      apiBaseUrl: "https://mianshiwen.cc/api/v1",
      token: "clean-close-token",
      onEvent: () => undefined,
      onState: state => states.push(state),
    });
    const started = transport.start();
    await vi.runAllTicks();
    await started;
    const oldSocket = FakeWebSocket.instances[0]!;
    acceptConnection(oldSocket);
    const staleClose = oldSocket.onclose;
    oldSocket.close(1000);
    await vi.advanceTimersByTimeAsync(5_500);
    expect(FakeWebSocket.instances).toHaveLength(2);
    const currentSocket = FakeWebSocket.instances[1]!;
    acceptConnection(currentSocket);
    staleClose?.({ code: 1006 });
    await vi.advanceTimersByTimeAsync(5_500);
    expect(FakeWebSocket.instances).toHaveLength(2);
    expect(states).toContain("reconnecting");
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
    acceptConnection(FakeWebSocket.instances[0]!, -1, 8);
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
    acceptConnection(FakeWebSocket.instances[0]!);
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
    acceptConnection(FakeWebSocket.instances[0]!);
    transport.enqueue({ sourceKind: "system", sourceId: "loopback", sequence: 0, isFinal: false, capturedAtMs: Date.now() });
    FakeWebSocket.instances[0]!.close(1008);
    expect(terminals).toHaveLength(1);
    expect(terminals[0]).toMatchObject({ code: 1008, reason: "publisher-credential-rejected" });
    expect(terminals[0]?.pending).toHaveLength(1);
  });

  it("replaces a stalled high-sequence publisher with a fresh sequence-zero publisher", async () => {
    vi.stubGlobal("window", { location: { href: "https://mianshiwen.cc/interviews/session" }, setTimeout, clearTimeout });
    vi.stubGlobal("WebSocket", FakeWebSocket);
    const terminals: Array<{ reason: string; pending: readonly Record<string, unknown>[] }> = [];
    const oldTransport = new MultiplexedRealtimeTransport({
      apiBaseUrl: "https://mianshiwen.cc/api/v1",
      token: "old-high-sequence-token",
      onEvent: () => undefined,
      onState: () => undefined,
      onTerminal: terminal => terminals.push(terminal),
    });
    await oldTransport.start();
    acceptConnection(FakeWebSocket.instances[0]!, -1, 268);
    oldTransport.enqueue({ sourceKind: "system", sourceId: "loopback", sequence: 269, isFinal: false });
    expect(decodeEnvelope(FakeWebSocket.instances[0]!.sent[0]!)).toMatchObject({ sourceKind: "system", sequence: 269 });
    FakeWebSocket.instances[0]!.close(1008);
    expect(terminals).toEqual([expect.objectContaining({
      reason: "publisher-credential-rejected",
      pending: [expect.objectContaining({ sequence: 269 })],
    })]);

    const acknowledgements: unknown[] = [];
    const replacement = new MultiplexedRealtimeTransport({
      apiBaseUrl: "https://mianshiwen.cc/api/v1",
      token: "fresh-replacement-token",
      onEvent: event => acknowledgements.push(event),
      onState: () => undefined,
    });
    await replacement.start();
    acceptConnection(FakeWebSocket.instances[1]!, -1, -1);
    replacement.enqueue({ sourceKind: "system", sourceId: "loopback", sequence: 0, isFinal: false });
    expect(decodeEnvelope(FakeWebSocket.instances[1]!.sent[0]!)).toMatchObject({ sourceKind: "system", sequence: 0 });
    FakeWebSocket.instances[1]!.serverEvent({ kind: "frame-accepted", payload: { sourceKind: "system", sourceId: "loopback", sequence: 0 } });
    expect(acknowledgements).toContainEqual(expect.objectContaining({
      kind: "frame-accepted",
      payload: expect.objectContaining({ sourceKind: "system", sequence: 0 }),
    }));
    replacement.stop();
  });

  it("exposes retained server offsets so a replacement never restarts below the backend boundary", async () => {
    vi.stubGlobal("window", { location: { href: "https://mianshiwen.cc/interviews/session" }, setTimeout, clearTimeout });
    vi.stubGlobal("WebSocket", FakeWebSocket);
    const transport = new MultiplexedRealtimeTransport({
      apiBaseUrl: "https://mianshiwen.cc/api/v1",
      token: "retained-offset-token",
      onEvent: () => undefined,
      onState: () => undefined,
    });
    await transport.start();
    const offsetsReady = transport.waitForResumeOffsets();
    acceptConnection(FakeWebSocket.instances[0]!, -1, 3_599);
    const offsets = await offsetsReady;
    const sequencer = new SourceFrameSequencer();
    sequencer.alignNext("system", offsets.system + 1);
    const resumed = createAudioFrame(sequencer, {
      sessionId: "session",
      deviceId: "device",
      sourceId: "loopback",
      sourceKind: "system",
      capturedAtMs: Date.now(),
      durationMs: 100,
      payload: new Uint8Array([1, 2]),
    });
    transport.enqueue({ ...resumed, audioBase64: btoa("ab") });
    expect(decodeEnvelope(FakeWebSocket.instances[0]!.sent[0]!)).toMatchObject({ sourceKind: "system", sequence: 3_600 });
    transport.stop();
  });

  it("bounds unacknowledged websocket writes per channel", async () => {
    vi.stubGlobal("window", { location: { href: "https://mianshiwen.cc/interviews/session" }, setTimeout, clearTimeout });
    vi.stubGlobal("WebSocket", FakeWebSocket);
    const transport = new MultiplexedRealtimeTransport({
      apiBaseUrl: "https://mianshiwen.cc/api/v1",
      token: "window-token",
      onEvent: () => undefined,
      onState: () => undefined,
    });
    await transport.start();
    acceptConnection(FakeWebSocket.instances[0]!);
    for (let sequence = 0; sequence < 40; sequence += 1) {
      transport.enqueue({ sourceKind: "system", sourceId: "loopback", sequence, isFinal: false });
    }
    expect(FakeWebSocket.instances[0]!.sent).toHaveLength(8);
    FakeWebSocket.instances[0]!.serverEvent({ kind: "frame-accepted", payload: { sourceKind: "system", sequence: 3 } });
    expect(FakeWebSocket.instances[0]!.sent).toHaveLength(12);
    transport.stop();
  });

  it("waits for authoritative resume offsets and skips frames already accepted by the backend", async () => {
    vi.stubGlobal("window", { location: { href: "https://mianshiwen.cc/interviews/session" }, setTimeout, clearTimeout });
    vi.stubGlobal("WebSocket", FakeWebSocket);
    const transport = new MultiplexedRealtimeTransport({
      apiBaseUrl: "https://mianshiwen.cc/api/v1",
      token: "resume-offset-token",
      onEvent: () => undefined,
      onState: () => undefined,
    });
    await transport.start();
    transport.enqueue({ sourceKind: "microphone", sourceId: "mic", sequence: 0, isFinal: false });
    transport.enqueue({ sourceKind: "microphone", sourceId: "mic", sequence: 1, isFinal: false });
    expect(FakeWebSocket.instances[0]!.sent).toHaveLength(0);
    acceptConnection(FakeWebSocket.instances[0]!, 0, -1);
    expect(FakeWebSocket.instances[0]!.sent.map(decodeEnvelope).map(item => item.sequence)).toEqual([1]);
    transport.stop();
  });

  it("discards retired-generation frames enqueued after authoritative offsets", async () => {
    vi.stubGlobal("window", { location: { href: "https://mianshiwen.cc/interviews/session" }, setTimeout, clearTimeout });
    vi.stubGlobal("WebSocket", FakeWebSocket);
    const events: Array<{ kind?: string; payload?: Record<string, unknown> }> = [];
    const transport = new MultiplexedRealtimeTransport({
      apiBaseUrl: "https://mianshiwen.cc/api/v1",
      token: "atomic-resume-token",
      onEvent: event => events.push(event),
      onState: () => undefined,
    });
    await transport.start();
    acceptConnection(FakeWebSocket.instances[0]!, 14, 52);
    transport.enqueue({ sourceKind: "microphone", sourceId: "retired-headset", sequence: 7, isFinal: false });
    transport.enqueue({ sourceKind: "microphone", sourceId: "default-mic", sequence: 15, isFinal: false });
    expect(FakeWebSocket.instances[0]!.sent.map(decodeEnvelope).map(item => item.sequence)).toEqual([15]);
    expect(events).toContainEqual(expect.objectContaining({
      kind: "delivery-diagnostics",
      payload: expect.objectContaining({ reason: "retired-generation-frame-discarded", sequence: 7, resumeOffset: 14 }),
    }));
    transport.stop();
  });

  it("reports a saturated per-channel window without losing its oldest pending age", async () => {
    vi.useFakeTimers();
    vi.setSystemTime(1_000);
    vi.stubGlobal("window", { location: { href: "https://mianshiwen.cc/interviews/session" }, setTimeout, clearTimeout });
    vi.stubGlobal("WebSocket", FakeWebSocket);
    const transport = new MultiplexedRealtimeTransport({
      apiBaseUrl: "https://mianshiwen.cc/api/v1",
      token: "production-deadlock-token",
      onEvent: () => undefined,
      onState: () => undefined,
    });
    await transport.start();
    acceptConnection(FakeWebSocket.instances[0]!);
    for (let sequence = 0; sequence < 32; sequence += 1) {
      vi.setSystemTime(1_000 + sequence * 100);
      transport.enqueue({ sourceKind: "microphone", sourceId: "mic", sequence, isFinal: false, capturedAtMs: Date.now() });
    }
    const progress = transport.progressSnapshot("microphone");
    expect(FakeWebSocket.instances[0]!.sent).toHaveLength(8);
    expect(progress).toMatchObject({ inFlightFrames: 8, queuedFrames: 32, oldestUnacknowledgedAtMs: 1_000, lastSentSequence: 7, lastAcknowledgedSequence: -1 });
    transport.stop();
  });

  it("opens the circuit after the bounded resend budget is exhausted", async () => {
    vi.useFakeTimers();
    vi.setSystemTime(1_000);
    vi.stubGlobal("window", { location: { href: "https://mianshiwen.cc/interviews/session" }, setTimeout, clearTimeout });
    vi.stubGlobal("WebSocket", FakeWebSocket);
    const recoveries: Array<{ reason: string; resetSequence?: boolean }> = [];
    const started = new MultiplexedRealtimeTransport({
      apiBaseUrl: "https://mianshiwen.cc/api/v1",
      token: "circuit-token",
      onEvent: () => undefined,
      onState: () => undefined,
      onTerminal: input => recoveries.push(input),
    });
    const connecting = started.start();
    await vi.runAllTicks();
    await connecting;
    acceptConnection(FakeWebSocket.instances[0]!, -1, 4);
    started.enqueue({ sourceKind: "system", sourceId: "loopback", sequence: 5, isFinal: false });
    for (let attempt = 0; attempt < 4; attempt += 1) {
      vi.setSystemTime(2_000 + attempt * 600);
      FakeWebSocket.instances[0]!.serverEvent({ kind: "sequence-gap", payload: { sourceKind: "system", expected: 5, received: 6 } });
    }
    expect(FakeWebSocket.instances[0]!.sent).toHaveLength(4);
    expect(recoveries).toEqual([expect.objectContaining({ reason: "sequence-gap-retry-budget-exhausted", resetSequence: true })]);
  });

  it("requests a fresh sequence when the backend expects an unavailable frame", async () => {
    vi.stubGlobal("window", { location: { href: "https://mianshiwen.cc/interviews/session" }, setTimeout, clearTimeout });
    vi.stubGlobal("WebSocket", FakeWebSocket);
    const recoveries: Array<{ reason: string; resetSequence?: boolean }> = [];
    const transport = new MultiplexedRealtimeTransport({
      apiBaseUrl: "https://mianshiwen.cc/api/v1",
      token: "reset-token",
      onEvent: () => undefined,
      onState: () => undefined,
      onTerminal: input => recoveries.push(input),
    });
    await transport.start();
    acceptConnection(FakeWebSocket.instances[0]!);
    transport.enqueue({ sourceKind: "microphone", sourceId: "mic", sequence: 0, isFinal: false });
    FakeWebSocket.instances[0]!.serverEvent({ kind: "frame-accepted", payload: { sourceKind: "microphone", sequence: 0 } });
    FakeWebSocket.instances[0]!.serverEvent({ kind: "sequence-gap", payload: { sourceKind: "microphone", expected: 0, received: 9 } });
    expect(recoveries).toEqual([expect.objectContaining({ reason: "sequence-gap-frame-unavailable", resetSequence: true })]);
  });

  it("soaks dual-channel traffic through an ACK stall and clean reconnect without unbounded queues", async () => {
    vi.useFakeTimers();
    vi.setSystemTime(1_000);
    vi.stubGlobal("window", { location: { href: "https://mianshiwen.cc/interviews/session" }, setTimeout, clearTimeout, setInterval, clearInterval });
    vi.stubGlobal("WebSocket", FakeWebSocket);
    const diagnostics = new RealtimeTransportDiagnostics("dual-channel-soak", () => undefined, 10_000, 1_000);
    const transport = new MultiplexedRealtimeTransport({
      apiBaseUrl: "https://mianshiwen.cc/api/v1",
      token: "dual-channel-soak-token",
      diagnostics,
      onEvent: () => undefined,
      onState: () => undefined,
    });
    const started = transport.start();
    await vi.runAllTicks();
    await started;
    const firstSocket = FakeWebSocket.instances[0]!;
    acceptConnection(firstSocket);

    for (let sequence = 0; sequence < 500; sequence += 1) {
      for (const sourceKind of ["microphone", "system"] as const) {
        transport.enqueue({ sourceKind, sourceId: sourceKind, sequence, isFinal: false, capturedAtMs: Date.now() });
        firstSocket.serverEvent({ kind: "frame-accepted", payload: { sourceKind, sourceId: sourceKind, sequence } });
      }
    }
    for (let sequence = 500; sequence < 540; sequence += 1) {
      transport.enqueue({ sourceKind: "microphone", sourceId: "microphone", sequence, isFinal: false, capturedAtMs: Date.now() });
      transport.enqueue({ sourceKind: "system", sourceId: "system", sequence, isFinal: false, capturedAtMs: Date.now() });
      firstSocket.serverEvent({ kind: "frame-accepted", payload: { sourceKind: "system", sourceId: "system", sequence } });
    }
    expect(transport.progressSnapshot("microphone")).toMatchObject({ inFlightFrames: 8, queuedFrames: 40, lastAcknowledgedSequence: 499 });

    firstSocket.close(1000);
    await vi.advanceTimersByTimeAsync(5_500);
    const replacement = FakeWebSocket.instances[1]!;
    acceptConnection(replacement, 499, 539);
    let observedSends = 0;
    while (transport.progressSnapshot("microphone").queuedFrames > 0) {
      const newlySent = replacement.sent.slice(observedSends).map(decodeEnvelope).filter(item => item.sourceKind === "microphone");
      expect(newlySent.length).toBeGreaterThan(0);
      observedSends = replacement.sent.length;
      const latest = Math.max(...newlySent.map(item => Number(item.sequence)));
      replacement.serverEvent({ kind: "frame-accepted", payload: { sourceKind: "microphone", sourceId: "microphone", sequence: latest } });
    }

    for (let sequence = 540; sequence < 2_000; sequence += 1) {
      for (const sourceKind of ["microphone", "system"] as const) {
        transport.enqueue({ sourceKind, sourceId: sourceKind, sequence, isFinal: false, capturedAtMs: Date.now() });
        replacement.serverEvent({ kind: "frame-accepted", payload: { sourceKind, sourceId: sourceKind, sequence } });
      }
    }
    const snapshot = diagnostics.publish(20_000);
    expect(transport.pendingPayloads()).toHaveLength(0);
    expect(snapshot.MIC.maximum_send_count_for_one_seq).toBeLessThanOrEqual(2);
    expect(snapshot.SYSTEM.maximum_send_count_for_one_seq).toBe(1);
    expect(snapshot.MIC.retransmit_queue_depth).toBe(0);
    expect(snapshot.SYSTEM.retransmit_queue_depth).toBe(0);
    transport.stop();
  });
});
