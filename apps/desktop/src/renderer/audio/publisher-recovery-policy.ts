export interface RecoveryTimerHost {
  readonly setTimeout: (handler: () => void, timeoutMs: number) => number;
  readonly clearTimeout: (timer: number) => void;
}

interface PendingAck<TTransport extends object> {
  readonly transport: TTransport;
  readonly timeoutMs: number;
  timer: number | null;
  readonly resolve: () => void;
  readonly reject: (error: Error) => void;
}

export class FreshTransportAckGate<TTransport extends object> {
  private pending: PendingAck<TTransport> | null = null;

  constructor(private readonly timers: RecoveryTimerHost) {}

  wait(transport: TTransport, timeoutMs: number): Promise<void> {
    this.cancel("replacement-publisher-superseded");
    return new Promise<void>((resolve, reject) => {
      this.pending = { transport, timeoutMs, timer: null, resolve, reject };
    });
  }

  markMediaPending(transport: TTransport): boolean {
    const pending = this.pending;
    if (pending?.transport !== transport) return false;
    if (pending.timer !== null) return true;
    pending.timer = this.timers.setTimeout(() => {
      if (this.pending?.transport !== transport) return;
      this.pending = null;
      pending.reject(new Error("replacement-publisher-ack-timeout"));
    }, pending.timeoutMs);
    return true;
  }

  isWaitingFor(transport: TTransport): boolean {
    return this.pending?.transport === transport;
  }

  acknowledge(transport: TTransport): boolean {
    if (this.pending?.transport !== transport) return false;
    const pending = this.pending;
    this.pending = null;
    if (pending.timer !== null) this.timers.clearTimeout(pending.timer);
    pending.resolve();
    return true;
  }

  fail(transport: TTransport, reason: string): boolean {
    if (this.pending?.transport !== transport) return false;
    const pending = this.pending;
    this.pending = null;
    if (pending.timer !== null) this.timers.clearTimeout(pending.timer);
    pending.reject(new Error(reason));
    return true;
  }

  cancel(reason: string): void {
    const pending = this.pending;
    if (!pending) return;
    this.pending = null;
    if (pending.timer !== null) this.timers.clearTimeout(pending.timer);
    pending.reject(new Error(reason));
  }
}

const MAX_PUBLISHER_RECOVERY_DELAY_MS = 5_000;

/**
 * Delay before the next replacement-publisher attempt. Attempts remain
 * single-flight in DesktopRealtimePublisher; this helper only bounds how
 * aggressively a live session retries during a transient outage.
 */
export const publisherRecoveryDelayMs = (failedAttempts: number, jitterMs = 0): number => {
  const exponent = Math.max(0, Math.min(5, Math.trunc(failedAttempts) - 1));
  const boundedJitter = Math.max(0, Math.min(150, Math.trunc(jitterMs)));
  return Math.min(MAX_PUBLISHER_RECOVERY_DELAY_MS, 250 * 2 ** exponent) + boundedJitter;
};

export type RecoveryChannel = "microphone" | "system";

export class ChannelForwardProgressGate<TTransport extends object> {
  private transport: TTransport | null = null;
  private readonly produced = new Set<RecoveryChannel>();
  private readonly acknowledged = new Set<RecoveryChannel>();

  activate(transport: TTransport): void {
    this.transport = transport;
    this.produced.clear();
    this.acknowledged.clear();
  }

  markMediaProduced(transport: TTransport, channel: RecoveryChannel): boolean {
    if (this.transport !== transport) return false;
    this.produced.add(channel);
    return true;
  }

  acknowledge(transport: TTransport, channel: RecoveryChannel): boolean {
    if (this.transport !== transport) return false;
    this.acknowledged.add(channel);
    return true;
  }

  pendingChannels(transport: TTransport): readonly RecoveryChannel[] {
    if (this.transport !== transport) return [];
    return [...this.produced].filter(channel => !this.acknowledged.has(channel));
  }

  allProducedChannelsAcknowledged(transport: TTransport): boolean {
    return this.transport === transport && this.pendingChannels(transport).length === 0;
  }

  clear(transport?: TTransport): void {
    if (transport && this.transport !== transport) return;
    this.transport = null;
    this.produced.clear();
    this.acknowledged.clear();
  }
}
