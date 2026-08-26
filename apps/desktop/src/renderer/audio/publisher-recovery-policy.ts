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

export class ReplacementPublisherBudget {
  private attempts = 0;

  constructor(readonly maximumAttempts: number) {}

  claimAttempt(): boolean {
    if (this.attempts >= this.maximumAttempts) return false;
    this.attempts += 1;
    return true;
  }

  recordAcknowledgement(hasPendingFrames: boolean): void {
    if (!hasPendingFrames) this.attempts = 0;
  }

  get usedAttempts(): number {
    return this.attempts;
  }
}
