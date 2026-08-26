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
  readonly onTerminal?: (input: { readonly code: number; readonly reason: string; readonly pending: readonly Record<string, unknown>[]; readonly resetSequence?: boolean }) => void;
  readonly diagnostics?: RealtimeTransportDiagnostics;
}

interface GapRecoveryState {
  readonly expected: number;
  attempts: number;
  lastAttemptAtMs: number;
}

export interface RealtimeResumeOffsets {
  readonly microphone: number;
  readonly system: number;
}

export interface RealtimeChannelTransportProgress {
  readonly inFlightFrames: number;
  readonly queuedFrames: number;
  readonly oldestUnacknowledgedAtMs: number | null;
  readonly lastSentSequence: number | null;
  readonly lastAcknowledgedSequence: number | null;
}

const MAX_IN_FLIGHT_FRAMES_PER_CHANNEL = 8;
const MAX_GAP_RESENDS_PER_SEQUENCE = 3;
const GAP_RESEND_COOLDOWN_MS = 500;

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
  private readonly gapRecoveryBySource = new Map<RealtimeAudioChannel, GapRecoveryState>();
  private readyForFrames = false;
  private recoveryRequested = false;
  private resumeOffsets: RealtimeResumeOffsets | null = null;
  private socketGeneration = 0;
  private readonly lastAcknowledgedBySource = new Map<RealtimeAudioChannel, number>();
  private readonly sentAtByFrame = new Map<string, number>();
  private readonly resumeOffsetWaiters = new Set<{
    readonly resolve: (offsets: RealtimeResumeOffsets) => void;
    readonly reject: (error: Error) => void;
    readonly timer: number;
  }>();

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
    const authoritativeOffset = this.resumeOffsets?.[sourceKind];
    if (typeof authoritativeOffset === "number" && sequence <= authoritativeOffset && !isTerminal) {
      this.options.onEvent({ kind: "delivery-diagnostics", payload: {
        sourceKind,
        sourceId,
        reason: "retired-generation-frame-discarded",
        sequence,
        resumeOffset: authoritativeOffset,
        pendingFrames: this.queue.filter(item => item.sourceKind === sourceKind).length,
      } });
      return;
    }
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

  progressSnapshot(sourceKind: RealtimeAudioChannel): RealtimeChannelTransportProgress {
    const channelQueue = this.queue.filter(item => item.sourceKind === sourceKind);
    const inFlightFrames = [...this.sent].filter(key => key.startsWith(`${sourceKind}:`)).length;
    const oldestSent = channelQueue
      .map(item => this.sentAtByFrame.get(`${item.sourceKind}:${item.sequence}`) ?? 0)
      .filter(value => Number.isFinite(value) && value > 0);
    return {
      inFlightFrames,
      queuedFrames: channelQueue.length,
      oldestUnacknowledgedAtMs: oldestSent.length > 0 ? Math.min(...oldestSent) : null,
      lastSentSequence: this.lastSequenceFromKeys(sourceKind),
      lastAcknowledgedSequence: this.lastAcknowledgedBySource.get(sourceKind) ?? null,
    };
  }

  waitForResumeOffsets(timeoutMs = 5_000): Promise<RealtimeResumeOffsets> {
    if (this.resumeOffsets) return Promise.resolve(this.resumeOffsets);
    return new Promise<RealtimeResumeOffsets>((resolve, reject) => {
      const waiter = {
        resolve,
        reject,
        timer: window.setTimeout(() => {
          this.resumeOffsetWaiters.delete(waiter);
          reject(new Error("publisher-resume-offset-timeout"));
        }, timeoutMs),
      };
      this.resumeOffsetWaiters.add(waiter);
    });
  }

  stop(): void {
    this.stopped = true;
    if (this.reconnectTimer !== null) window.clearTimeout(this.reconnectTimer);
    this.reconnectTimer = null;
    this.socket?.close(1000, "interview-stopped");
    this.socket = null;
    this.queue = [];
    this.sent.clear();
    this.sentAtByFrame.clear();
    this.terminalResends.clear();
    this.lastSentAtBySource.clear();
    this.gapRecoveryBySource.clear();
    this.readyForFrames = false;
    this.recoveryRequested = false;
    for (const waiter of this.resumeOffsetWaiters) {
      window.clearTimeout(waiter.timer);
      waiter.reject(new Error("publisher-transport-stopped"));
    }
    this.resumeOffsetWaiters.clear();
    this.publishQueueDepths();
  }

  private connect(): Promise<void> {
    if (this.connecting) return this.connecting;
    this.connecting = new Promise<void>((resolve, reject) => {
      const socket = new WebSocket(socketUrl(this.options.apiBaseUrl, this.options.token));
      const generation = ++this.socketGeneration;
      this.socket = socket;
      const timeout = window.setTimeout(() => socket.close(4000, "connect-timeout"), 5000);
      socket.onopen = () => {
        if (this.socket !== socket || generation !== this.socketGeneration) return;
        window.clearTimeout(timeout);
        this.reconnectAttempt = 0;
        this.options.onState("connected");
        this.publishDiagnostics();
        resolve();
      };
      socket.onmessage = (message) => {
        if (this.socket !== socket || generation !== this.socketGeneration) return;
        try {
          const event = JSON.parse(String(message.data)) as { kind?: string; payload?: Record<string, unknown> };
          if (event.kind === "connection-state") this.applyResumeOffsets(event.payload);
          if (event.kind === "frame-accepted" || event.kind === "terminal-accepted") {
            this.acknowledge(event.payload);
            const sourceKind = event.payload?.sourceKind;
            if (sourceKind === "microphone" || sourceKind === "system") {
              event.payload = {
                ...event.payload,
                pendingFrames: this.queue.filter(item => item.sourceKind === sourceKind).length,
                lastAckAtMs: Date.now(),
              };
            }
          }
          if (event.kind === "sequence-gap") this.handleGap(event.payload);
          this.options.onEvent(event);
        } catch {
          this.options.onEvent({ kind: "degraded", payload: { reason: "invalid-server-event" } });
        }
      };
      socket.onerror = () => {
        if (this.socket !== socket || generation !== this.socketGeneration) return;
        window.clearTimeout(timeout);
        reject(new Error("publisher_websocket_failed"));
      };
      socket.onclose = (event) => {
        window.clearTimeout(timeout);
        if (this.socket !== socket || generation !== this.socketGeneration) return;
        this.socket = null;
        this.connecting = null;
        this.readyForFrames = false;
        this.sent.clear();
        this.sentAtByFrame.clear();
        if (this.stopped || this.recoveryRequested) return;
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
    if (!this.readyForFrames || this.socket?.readyState !== WebSocket.OPEN) return;
    for (const channel of ["microphone", "system"] as const) {
      const inFlight = [...this.sent].reduce((count, key) => count + (key.startsWith(`${channel}:`) ? 1 : 0), 0);
      let available = Math.max(0, MAX_IN_FLIGHT_FRAMES_PER_CHANNEL - inFlight);
      if (available === 0) continue;
      for (const item of this.queue) {
        if (item.sourceKind !== channel || available === 0) continue;
        const key = `${item.sourceKind}:${item.sequence}`;
        if (this.sent.has(key)) continue;
        this.sendItem(item, reason);
        available -= 1;
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
    this.lastAcknowledgedBySource.set(sourceKind, Math.max(sequence, this.lastAcknowledgedBySource.get(sourceKind) ?? -1));
    this.queue = this.queue.filter(item => terminalId ? item.terminalId !== terminalId : item.sourceKind !== sourceKind || item.sequence > sequence);
    for (const key of this.sent) {
      const [channel, rawSequence] = key.split(":");
      if (channel === sourceKind && Number(rawSequence) <= sequence) {
        this.sent.delete(key);
        this.sentAtByFrame.delete(key);
      }
    }
    if (terminalId) this.terminalResends.delete(terminalId);
    this.gapRecoveryBySource.delete(sourceKind);
    this.publishQueueDepths();
    this.publishDiagnostics(sourceKind, Date.now(), terminalId ? Date.now() : undefined);
    this.flush();
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
    const nowMs = Date.now();
    const previous = this.gapRecoveryBySource.get(sourceKind);
    if (previous?.expected === expected && nowMs - previous.lastAttemptAtMs < GAP_RESEND_COOLDOWN_MS) return;
    const attempts = previous?.expected === expected ? previous.attempts + 1 : 1;
    if (attempts > MAX_GAP_RESENDS_PER_SEQUENCE) {
      this.requestFreshSequence("sequence-gap-retry-budget-exhausted", sourceKind, expected);
      return;
    }
    this.queue = this.queue.filter(item => item.sourceKind !== sourceKind || item.sequence >= expected);
    const expectedItem = this.queue.find(item => item.sourceKind === sourceKind && item.sequence === expected);
    if (!expectedItem) {
      this.requestFreshSequence("sequence-gap-frame-unavailable", sourceKind, expected);
      return;
    }
    this.gapRecoveryBySource.set(sourceKind, { expected, attempts, lastAttemptAtMs: nowMs });
    this.sent.delete(`${sourceKind}:${expected}`);
    this.sendItem(expectedItem, "sequence-gap");
    this.publishQueueDepths();
  }

  private applyResumeOffsets(payload?: Record<string, unknown>): void {
    const resumeOffsets = payload?.resumeOffsets;
    if (typeof resumeOffsets !== "object" || resumeOffsets === null) return;
    const acceptedOffsets: Record<RealtimeAudioChannel, number> = { microphone: -1, system: -1 };
    for (const channel of ["microphone", "system"] as const) {
      const offset = (resumeOffsets as Record<string, unknown>)[channel];
      if (typeof offset !== "number" || !Number.isInteger(offset)) continue;
      acceptedOffsets[channel] = offset;
      this.lastAcknowledgedBySource.set(channel, offset);
      // A resume offset proves only that the backend observed a sequence. It
      // does not prove that an isFinal frame reached terminal admission. Keep
      // terminals until an explicit terminal-accepted event names their id.
      this.queue = this.queue.filter(item => item.sourceKind !== channel || item.sequence > offset || item.isTerminal);
      for (const key of this.sent) {
        const [sourceKind, rawSequence] = key.split(":");
        if (sourceKind === channel && Number(rawSequence) <= offset) {
          this.sent.delete(key);
          this.sentAtByFrame.delete(key);
        }
      }
      const firstPending = this.queue.find(item => item.sourceKind === channel);
      if (firstPending && firstPending.sequence > offset + 1) {
        this.requestFreshSequence("resume-offset-frame-unavailable", channel, offset + 1);
        return;
      }
    }
    this.resumeOffsets = acceptedOffsets;
    this.readyForFrames = true;
    for (const waiter of this.resumeOffsetWaiters) {
      window.clearTimeout(waiter.timer);
      waiter.resolve(acceptedOffsets);
    }
    this.resumeOffsetWaiters.clear();
    this.publishQueueDepths();
    this.flush();
  }

  private sendItem(item: QueuedEnvelope, reason: "normal" | "sequence-gap"): void {
    if (!this.readyForFrames || this.socket?.readyState !== WebSocket.OPEN) return;
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
    const frameKey = `${item.sourceKind}:${item.sequence}`;
    this.sent.add(frameKey);
    if (!this.sentAtByFrame.has(frameKey)) this.sentAtByFrame.set(frameKey, desktopPublisherFlushAtMs);
    if (item.terminalId) {
      const resendCount = this.terminalResends.get(item.terminalId) ?? 0;
      this.terminalResends.set(item.terminalId, resendCount + 1);
    }
  }

  private requestFreshSequence(reason: string, sourceKind: RealtimeAudioChannel, expected: number): void {
    if (this.recoveryRequested || this.stopped) return;
    this.recoveryRequested = true;
    this.readyForFrames = false;
    const pending = this.pendingPayloads();
    this.options.onState("failed");
    this.options.onEvent({ kind: "degraded", payload: { reason, sourceKind, expected, pendingFrames: pending.length } });
    this.options.onTerminal?.({ code: 1013, reason, pending, resetSequence: true });
    this.socket?.close(1013, reason);
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
      const progress = this.progressSnapshot(channel);
      this.options.diagnostics?.setDeliveryProgress(channel, {
        transportGeneration: this.socketGeneration,
        inFlightFrames: progress.inFlightFrames,
        oldestUnacknowledgedAtMs: progress.oldestUnacknowledgedAtMs,
        lastGenerationSentSeq: progress.lastSentSequence,
        lastGenerationAckedSeq: progress.lastAcknowledgedSequence,
      });
    }
  }

  private lastSequenceFromKeys(sourceKind: RealtimeAudioChannel): number | null {
    const sequences = [...this.sent]
      .filter(key => key.startsWith(`${sourceKind}:`))
      .map(key => Number(key.slice(sourceKind.length + 1)))
      .filter(Number.isFinite);
    return sequences.length > 0 ? Math.max(...sequences) : null;
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
