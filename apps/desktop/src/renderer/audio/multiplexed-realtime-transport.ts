import { REALTIME_PROTOCOL_VERSION, type RealtimeAudioChannel } from "@offersteady/protocol";
import type { RealtimeTransportDiagnostics } from "./realtime-transport-diagnostics";

interface QueuedEnvelope {
  readonly sourceKind: RealtimeAudioChannel;
  readonly sourceId: string;
  readonly sequence: number;
  readonly payload: Record<string, unknown>;
  readonly isTerminal: boolean;
  readonly terminalId?: string;
}

interface TransportOptions {
  readonly apiBaseUrl: string;
  readonly token: string;
  readonly onEvent: (event: { readonly kind?: string; readonly payload?: Record<string, unknown> }) => void;
  readonly onState: (state: "connected" | "reconnecting" | "failed") => void;
  readonly onTerminal?: (input: { readonly code: number; readonly reason: string; readonly pending: readonly Record<string, unknown>[] }) => void;
  readonly diagnostics?: RealtimeTransportDiagnostics;
}

const socketUrl = (apiBaseUrl: string, token: string) => {
  const base = new URL(apiBaseUrl, window.location.href);
  base.protocol = base.protocol === "https:" ? "wss:" : "ws:";
  base.pathname = `${base.pathname.replace(/\/$/, "")}/realtime-speech/ingest-ws`;
  base.search = new URLSearchParams({ token, protocol: REALTIME_PROTOCOL_VERSION, media: "binary-v1" }).toString();
  return base.toString();
};

export class MultiplexedRealtimeTransport {
  private socket: WebSocket | null = null;
  private queue: QueuedEnvelope[] = [];
  private reconnectTimer: number | null = null;
  private reconnectAttempt = 0;
  private sent = new Set<string>();
  private stopped = false;
  private connecting: Promise<void> | null = null;
  private readonly maximumFrames = 256;
  private readonly droppedFramesBySource = new Map<RealtimeAudioChannel, number>();
  private reconnectCount = 0;
  private readonly terminalResends = new Map<string, number>();
  private readonly lastSentAtBySource = new Map<RealtimeAudioChannel, number>();

  constructor(private readonly options: TransportOptions) {}

  async start(): Promise<void> {
    this.stopped = false;
    await this.connect();
  }

  enqueue(payload: Record<string, unknown>): void {
    const sourceKind = payload.sourceKind;
    const sourceId = payload.sourceId;
    const sequence = payload.sequence;
    if ((sourceKind !== "microphone" && sourceKind !== "system") || typeof sourceId !== "string" || typeof sequence !== "number") return;
    const isTerminal = payload.isFinal === true;
    const terminalId = typeof payload.terminalId === "string" ? payload.terminalId : undefined;
    if (terminalId && this.queue.some(item => item.terminalId === terminalId)) return;
    const item: QueuedEnvelope = {
      sourceKind,
      sourceId,
      sequence,
      payload: { ...payload, sentAtMs: Date.now() },
      isTerminal,
      ...(terminalId ? { terminalId } : {}),
    };
    if (this.queue.length >= this.maximumFrames) {
      const firstInterim = this.queue.findIndex(queued => !queued.isTerminal);
      if (firstInterim < 0 && !isTerminal) {
        this.recordDrop(item, "desktop-buffer-terminal-reserved");
        return;
      }
      if (firstInterim < 0) {
        this.options.onEvent({ kind: "degraded", payload: {
          reason: "terminal-buffer-full",
          sourceKind,
          sourceId,
          terminalId,
          pendingFrames: this.queue.length,
        } });
        return;
      }
      const [dropped] = this.queue.splice(firstInterim, 1);
      if (dropped) this.recordDrop(dropped, "desktop-buffer-overflow");
    }
    this.queue.push(item);
    this.options.diagnostics?.recordPublisherFrame({
      channel: sourceKind,
      sequence,
      audioBytes: this.audioPayloadByteLength(payload),
      codec: payload.codec,
      sampleRateHz: payload.sampleRateHz,
      channels: payload.channels,
    });
    this.publishQueueDepths();
    this.publishDiagnostics(sourceKind);
    this.flush();
  }

  pendingPayloads(): readonly Record<string, unknown>[] {
    return this.queue.map(item => ({ ...item.payload }));
  }

  stop(): void {
    this.stopped = true;
    if (this.reconnectTimer !== null) window.clearTimeout(this.reconnectTimer);
    this.reconnectTimer = null;
    this.socket?.close(1000, "interview-stopped");
    this.socket = null;
    this.queue = [];
    this.sent.clear();
    this.terminalResends.clear();
    this.lastSentAtBySource.clear();
    this.publishQueueDepths();
  }

  private connect(): Promise<void> {
    if (this.connecting) return this.connecting;
    this.connecting = new Promise<void>((resolve, reject) => {
      const socket = new WebSocket(socketUrl(this.options.apiBaseUrl, this.options.token));
      this.socket = socket;
      const timeout = window.setTimeout(() => socket.close(4000, "connect-timeout"), 5000);
      socket.onopen = () => {
        window.clearTimeout(timeout);
        this.reconnectAttempt = 0;
        this.options.onState("connected");
        this.publishDiagnostics();
        this.flush();
        resolve();
      };
      socket.onmessage = (message) => {
        try {
          const event = JSON.parse(String(message.data)) as { kind?: string; payload?: Record<string, unknown> };
          if (event.kind === "frame-accepted" || event.kind === "terminal-accepted") this.acknowledge(event.payload);
          if (event.kind === "sequence-gap") this.handleGap(event.payload);
          this.options.onEvent(event);
        } catch {
          this.options.onEvent({ kind: "degraded", payload: { reason: "invalid-server-event" } });
        }
      };
      socket.onerror = () => {
        window.clearTimeout(timeout);
        reject(new Error("publisher_websocket_failed"));
      };
      socket.onclose = (event) => {
        window.clearTimeout(timeout);
        this.socket = null;
        this.connecting = null;
        this.sent.clear();
        if (this.stopped || event.code === 1000) return;
        if (event.code === 1002 || event.code === 1008) {
          this.options.onState("failed");
          this.options.onTerminal?.({
            code: event.code,
            reason: event.code === 1008 ? "publisher-credential-rejected" : "protocol-rejected",
            pending: this.pendingPayloads(),
          });
          return;
        }
        this.scheduleReconnect();
      };
    }).finally(() => { this.connecting = null; });
    return this.connecting;
  }

  private scheduleReconnect(): void {
    if (this.stopped || this.reconnectTimer !== null) return;
    this.options.onState("reconnecting");
    this.reconnectCount += 1;
    this.options.diagnostics?.recordReconnect();
    this.options.onEvent({ kind: "connection-state", payload: {
      state: "reconnecting",
      reconnectCount: this.reconnectCount,
      reconnectAttempt: this.reconnectAttempt + 1,
      pendingFrames: this.queue.length,
      oldestPendingFrameAgeMs: this.oldestPendingFrameAgeMs(),
    } });
    const delay = Math.min(5000, 250 * 2 ** this.reconnectAttempt) + Math.floor(Math.random() * 150);
    this.reconnectAttempt += 1;
    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = null;
      void this.connect().catch(() => this.scheduleReconnect());
    }, delay);
  }

  private flush(reason: "normal" | "sequence-gap" = "normal"): void {
    if (this.socket?.readyState !== WebSocket.OPEN) return;
    for (const item of this.queue) {
      const key = `${item.sourceKind}:${item.sequence}`;
      if (this.sent.has(key)) continue;
      // This timestamp is the actual WebSocket write boundary. The enqueue
      // timestamp is not a transport send and would hide local queue delay.
      const desktopPublisherFlushAtMs = Date.now();
      const diagnostics = typeof item.payload.diagnostics === "object" && item.payload.diagnostics !== null
        ? item.payload.diagnostics as Record<string, unknown>
        : {};
      const envelope = this.binaryEnvelope({
        ...item.payload,
        sentAtMs: desktopPublisherFlushAtMs,
        diagnostics: {
          ...diagnostics,
          desktopPublisherFlushAtMs,
          desktopWsSendAtMs: desktopPublisherFlushAtMs,
        },
      });
      this.socket.send(envelope);
      this.options.diagnostics?.recordWebSocketSend({
        channel: item.sourceKind,
        sequence: item.sequence,
        audioPayloadBytes: this.audioPayloadByteLength(item.payload),
        totalBytes: envelope.byteLength,
        sequenceGapRecovery: reason === "sequence-gap",
      });
      this.lastSentAtBySource.set(item.sourceKind, desktopPublisherFlushAtMs);
      this.sent.add(key);
      if (item.terminalId) {
        const resendCount = this.terminalResends.get(item.terminalId) ?? 0;
        this.terminalResends.set(item.terminalId, resendCount + 1);
      }
    }
    this.publishQueueDepths();
  }

  private binaryEnvelope(payload: Record<string, unknown>): ArrayBuffer {
    const audioBase64 = typeof payload.audioBase64 === "string" ? payload.audioBase64 : "";
    const headerPayload = { ...payload };
    delete headerPayload.audioBase64;
    const header = new TextEncoder().encode(JSON.stringify(headerPayload));
    const binary = atob(audioBase64);
    const output = new Uint8Array(4 + header.byteLength + binary.length);
    new DataView(output.buffer).setUint32(0, header.byteLength, false);
    output.set(header, 4);
    for (let index = 0; index < binary.length; index += 1) output[4 + header.byteLength + index] = binary.charCodeAt(index);
    return output.buffer;
  }

  private acknowledge(payload?: Record<string, unknown>): void {
    const sourceKind = payload?.sourceKind;
    const sequence = payload?.sequence;
    if ((sourceKind !== "microphone" && sourceKind !== "system") || typeof sequence !== "number") return;
    const terminalId = typeof payload?.terminalId === "string" ? payload.terminalId : undefined;
    this.options.diagnostics?.recordAck(sourceKind, sequence);
    this.queue = this.queue.filter(item => terminalId ? item.terminalId !== terminalId : item.sourceKind !== sourceKind || item.sequence > sequence);
    for (const key of this.sent) {
      const [channel, rawSequence] = key.split(":");
      if (channel === sourceKind && Number(rawSequence) <= sequence) this.sent.delete(key);
    }
    if (terminalId) this.terminalResends.delete(terminalId);
    this.publishQueueDepths();
    this.publishDiagnostics(sourceKind, Date.now(), terminalId ? Date.now() : undefined);
  }

  private recordDrop(item: QueuedEnvelope, reason: string): void {
    const droppedFrames = (this.droppedFramesBySource.get(item.sourceKind) ?? 0) + 1;
    this.droppedFramesBySource.set(item.sourceKind, droppedFrames);
    this.options.onEvent({ kind: "sequence-gap", payload: {
      sourceKind: item.sourceKind,
      sourceId: item.sourceId,
      sequence: item.sequence,
      reason,
      droppedFrames,
      pendingFrames: this.queue.length,
      oldestPendingFrameAgeMs: this.oldestPendingFrameAgeMs(),
    } });
  }

  private handleGap(payload?: Record<string, unknown>): void {
    const sourceKind = payload?.sourceKind;
    const expected = payload?.expected;
    if ((sourceKind !== "microphone" && sourceKind !== "system") || typeof expected !== "number") return;
    this.options.diagnostics?.recordSequenceGap(sourceKind);
    this.queue = this.queue.filter(item => item.sourceKind !== sourceKind || item.sequence >= expected);
    for (const key of this.sent) if (key.startsWith(`${sourceKind}:`)) this.sent.delete(key);
    this.publishQueueDepths();
    this.flush("sequence-gap");
  }

  private audioPayloadByteLength(payload: Record<string, unknown>): number {
    const audioBase64 = typeof payload.audioBase64 === "string" ? payload.audioBase64 : "";
    if (!audioBase64) return 0;
    const padding = audioBase64.endsWith("==") ? 2 : audioBase64.endsWith("=") ? 1 : 0;
    return Math.max(0, Math.floor(audioBase64.length * 3 / 4) - padding);
  }

  private publishQueueDepths(): void {
    for (const channel of ["microphone", "system"] as const) {
      this.options.diagnostics?.setRetransmitQueueDepth(
        channel,
        this.queue.reduce((count, item) => count + (item.sourceKind === channel ? 1 : 0), 0),
      );
    }
  }

  private oldestPendingFrameAgeMs(): number {
    const capturedAtMs = this.queue
      .map(item => Number(item.payload.capturedAtMs))
      .filter(value => Number.isFinite(value) && value > 0);
    if (capturedAtMs.length === 0) return 0;
    return Math.max(0, Date.now() - Math.min(...capturedAtMs));
  }

  private publishDiagnostics(sourceKind?: RealtimeAudioChannel, lastAckAtMs?: number, terminalAckAtMs?: number): void {
    const channels: readonly RealtimeAudioChannel[] = sourceKind ? [sourceKind] : ["microphone", "system"];
    for (const channel of channels) {
      const channelQueue = this.queue.filter(item => item.sourceKind === channel);
      const capturedAtMs = channelQueue
        .map(item => Number(item.payload.capturedAtMs))
        .filter(value => Number.isFinite(value) && value > 0);
      const pendingTerminal = channelQueue.find(item => item.isTerminal);
      this.options.onEvent({ kind: "delivery-diagnostics", payload: {
        sourceKind: channel,
        pendingFrames: channelQueue.length,
        oldestPendingFrameAgeMs: capturedAtMs.length > 0 ? Math.max(0, Date.now() - Math.min(...capturedAtMs)) : 0,
        droppedFrames: this.droppedFramesBySource.get(channel) ?? 0,
        reconnectCount: this.reconnectCount,
        ...(pendingTerminal ? {
          terminalPendingSinceMs: Number(pendingTerminal.payload.sentAtMs) || Number(pendingTerminal.payload.capturedAtMs) || Date.now(),
          terminalAgeMs: Math.max(0, Date.now() - (Number(pendingTerminal.payload.sentAtMs) || Number(pendingTerminal.payload.capturedAtMs) || Date.now())),
          terminalResendCount: pendingTerminal.terminalId ? Math.max(0, (this.terminalResends.get(pendingTerminal.terminalId) ?? 1) - 1) : 0,
        } : {}),
        ...(terminalAckAtMs ? { terminalAckAtMs } : {}),
        ...(lastAckAtMs ? { lastAckAtMs } : {}),
        ...(this.lastSentAtBySource.get(channel) ? { lastFrameSentAtMs: this.lastSentAtBySource.get(channel) } : {}),
      } });
    }
  }
}
