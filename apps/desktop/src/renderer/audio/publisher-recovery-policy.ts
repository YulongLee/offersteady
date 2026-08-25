export interface RecoveryTimerHost {
  readonly setTimeout: (handler: () => void, timeoutMs: number) => number;
  readonly clearTimeout: (timer: number) => void;
}

interface PendingAck<TTransport extends object> {
  readonly transport: TTransport;
  readonly timer: number;
  readonly resolve: () => void;
  readonly reject: (error: Error) => void;
}

export class FreshTransportAckGate<TTransport extends object> {
  private pending: PendingAck<TTransport> | null = null;

  constructor(private readonly timers: RecoveryTimerHost) {}

  wait(transport: TTransport, timeoutMs: number): Promise<void> {
    this.cancel("replacement-publisher-superseded");
    return new Promise<void>((resolve, reject) => {
      const timer = this.timers.setTimeout(() => {
        if (this.pending?.transport !== transport) return;
        this.pending = null;
        reject(new Error("replacement-publisher-ack-timeout"));
      }, timeoutMs);
      this.pending = { transport, timer, resolve, reject };
    });
  }

  acknowledge(transport: TTransport): boolean {
    if (this.pending?.transport !== transport) return false;
    const pending = this.pending;
    this.pending = null;
    this.timers.clearTimeout(pending.timer);
    pending.resolve();
    return true;
  }

  fail(transport: TTransport, reason: string): boolean {
    if (this.pending?.transport !== transport) return false;
    const pending = this.pending;
    this.pending = null;
    this.timers.clearTimeout(pending.timer);
    pending.reject(new Error(reason));
    return true;
  }

  cancel(reason: string): void {
    const pending = this.pending;
    if (!pending) return;
    this.pending = null;
    this.timers.clearTimeout(pending.timer);
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
