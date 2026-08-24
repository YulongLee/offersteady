import { REALTIME_PROTOCOL_VERSION, type RealtimeAudioChannel } from "@offersteady/protocol";

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
}

const socketUrl = (apiBaseUrl: string, token: string) => {
  const base = new URL(apiBaseUrl, window.location.href);
  base.protocol = base.protocol === "https:" ? "wss:" : "ws:";
  base.pathname = `${base.pathname.replace(/\/$/, "")}/realtime-speech/ingest-ws`;
  base.search = new URLSearchParams({ token, protocol: REALTIME_PROTOCOL_VERSION }).toString();
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

  private flush(): void {
    if (this.socket?.readyState !== WebSocket.OPEN) return;
    for (const item of this.queue) {
      const key = `${item.sourceKind}:${item.sequence}`;
      if (this.sent.has(key)) continue;
      this.socket.send(JSON.stringify(item.payload));
      this.sent.add(key);
      if (item.terminalId) {
        const resendCount = this.terminalResends.get(item.terminalId) ?? 0;
        this.terminalResends.set(item.terminalId, resendCount + 1);
      }
    }
  }

  private acknowledge(payload?: Record<string, unknown>): void {
    const sourceKind = payload?.sourceKind;
    const sequence = payload?.sequence;
    if ((sourceKind !== "microphone" && sourceKind !== "system") || typeof sequence !== "number") return;
    const terminalId = typeof payload?.terminalId === "string" ? payload.terminalId : undefined;
    this.queue = this.queue.filter(item => terminalId ? item.terminalId !== terminalId : item.sourceKind !== sourceKind || item.sequence > sequence);
    for (const key of this.sent) {
      const [channel, rawSequence] = key.split(":");
      if (channel === sourceKind && Number(rawSequence) <= sequence) this.sent.delete(key);
    }
    if (terminalId) this.terminalResends.delete(terminalId);
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
    this.queue = this.queue.filter(item => item.sourceKind !== sourceKind || item.sequence >= expected);
    for (const key of this.sent) if (key.startsWith(`${sourceKind}:`)) this.sent.delete(key);
    this.flush();
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
      } });
    }
  }
}
