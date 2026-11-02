export const DESKTOP_REGISTRATION_INTERVAL_MS = 15_000;
export const DESKTOP_REGISTRATION_TIMEOUT_MS = 8_000;
export const DESKTOP_CONNECTION_FRESHNESS_MS = 45_000;
export const DESKTOP_RECOVERY_MIN_INTERVAL_MS = 2_000;

export type DesktopRecoveryReason = "resume" | "online" | "focus" | "binding";
export type DesktopRegistrationReason = "startup" | "heartbeat" | DesktopRecoveryReason;
export type DesktopConnectionError = "registration-rejected" | "registration-failed" | "registration-timeout";

export interface DesktopRegistrationContext {
  readonly signal: AbortSignal;
  readonly generation: number;
  readonly startedAtMs: number;
  readonly reason: DesktopRegistrationReason;
  /** Guard external side effects after every awaited operation. */
  readonly isCurrent: () => boolean;
}

export interface DesktopConnectionSnapshot {
  readonly running: boolean;
  readonly inFlight: boolean;
  readonly online: boolean;
  readonly lastStartedAtMs: number | null;
  readonly lastSuccessAtMs: number | null;
  readonly lastFailureAtMs: number | null;
  readonly lastErrorCode: DesktopConnectionError | null;
  readonly consecutiveFailures: number;
  readonly attempts: number;
  readonly successes: number;
  readonly failures: number;
  readonly timeouts: number;
  readonly mergedRecoverySignals: number;
}

export interface DesktopConnectionDiagnostic extends DesktopConnectionSnapshot {
  readonly type: "desktop-connection";
  readonly event: "started" | "succeeded" | "failed" | "recovery-merged" | "stopped";
  readonly atMs: number;
  readonly durationMs: number | null;
  readonly successAgeMs: number | null;
}

interface RecoveryTimers {
  setTimeout(callback: () => void, delayMs: number): ReturnType<typeof setTimeout>;
  clearTimeout(timer: ReturnType<typeof setTimeout>): void;
  setInterval(callback: () => void, delayMs: number): ReturnType<typeof setInterval>;
  clearInterval(timer: ReturnType<typeof setInterval>): void;
}

export interface DesktopConnectionRecoveryPorts {
  /** Includes identity loading, request, and response consumption. */
  readonly register: (context: DesktopRegistrationContext) => Promise<boolean>;
  /** Synchronous notification only; binding verification remains with the caller. */
  readonly onSuccess?: (context: DesktopRegistrationContext) => void;
  readonly onDiagnostic?: (diagnostic: DesktopConnectionDiagnostic) => void;
  readonly now?: () => number;
  readonly timers?: RecoveryTimers;
}

interface RegistrationOperation {
  readonly context: DesktopRegistrationContext;
  readonly controller: AbortController;
  timeout: ReturnType<typeof setTimeout> | null;
}

/** A single owner for bounded heartbeats. It never creates sessions or captures. */
export class DesktopConnectionRecovery {
  private readonly now: () => number;
  private readonly timers: RecoveryTimers;
  private running = false;
  private disposed = false;
  private generation = 0;
  private interval: ReturnType<typeof setInterval> | null = null;
  private recoveryTimer: ReturnType<typeof setTimeout> | null = null;
  private pendingRecovery: DesktopRecoveryReason | null = null;
  private operation: RegistrationOperation | null = null;
  private contextController: AbortController | null = null;
  private lastStartedAtMs: number | null = null;
  private lastSuccessAtMs: number | null = null;
  private lastFailureAtMs: number | null = null;
  private lastErrorCode: DesktopConnectionError | null = null;
  private consecutiveFailures = 0;
  private attempts = 0;
  private successes = 0;
  private failures = 0;
  private timeouts = 0;
  private mergedRecoverySignals = 0;

  constructor(private readonly ports: DesktopConnectionRecoveryPorts) {
    this.now = ports.now ?? Date.now;
    this.timers = ports.timers ?? {
      setTimeout: (callback, delayMs) => setTimeout(callback, delayMs),
      clearTimeout: timer => clearTimeout(timer),
      setInterval: (callback, delayMs) => setInterval(callback, delayMs),
      clearInterval: timer => clearInterval(timer),
    };
  }

  start(): void {
    if (this.running || this.disposed) return;
    this.running = true;
    this.interval = this.timers.setInterval(() => {
      this.expireOverdueOperation();
      // A recovery immediately before this tick already refreshed the device.
      if (this.lastStartedAtMs !== null && this.now() - this.lastStartedAtMs < DESKTOP_RECOVERY_MIN_INTERVAL_MS) return;
      this.run("heartbeat");
    }, DESKTOP_REGISTRATION_INTERVAL_MS);
    this.run("startup");
  }

  recover(reason: DesktopRecoveryReason): void {
    if (!this.running || this.disposed) return;
    // Timers may themselves have been suspended; an overdue request must not
    // make resume wait for a timer callback that has not run yet.
    this.expireOverdueOperation();
    if (this.operation || this.recoveryTimer !== null) {
      this.pendingRecovery ??= reason;
      this.mergedRecoverySignals += 1;
      this.diagnose("recovery-merged");
      return;
    }
    this.scheduleRecovery(reason);
  }

  snapshot(): DesktopConnectionSnapshot {
    const successAgeMs = this.lastSuccessAtMs === null ? null : this.now() - this.lastSuccessAtMs;
    return {
      running: this.running,
      inFlight: this.operation !== null,
      online: this.running && successAgeMs !== null && successAgeMs >= 0 && successAgeMs < DESKTOP_CONNECTION_FRESHNESS_MS,
      lastStartedAtMs: this.lastStartedAtMs,
      lastSuccessAtMs: this.lastSuccessAtMs,
      lastFailureAtMs: this.lastFailureAtMs,
      lastErrorCode: this.lastErrorCode,
      consecutiveFailures: this.consecutiveFailures,
      attempts: this.attempts,
      successes: this.successes,
      failures: this.failures,
      timeouts: this.timeouts,
      mergedRecoverySignals: this.mergedRecoverySignals,
    };
  }

  stop(): void {
    if (!this.running) return;
    this.running = false;
    this.generation += 1;
    if (this.interval !== null) this.timers.clearInterval(this.interval);
    this.interval = null;
    this.clearRecoveryTimer();
    this.pendingRecovery = null;
    const timeout = this.operation?.timeout;
    if (timeout !== null && timeout !== undefined) this.timers.clearTimeout(timeout);
    this.operation = null;
    this.contextController?.abort();
    this.contextController = null;
    this.diagnose("stopped");
  }

  dispose(): void {
    this.stop();
    this.disposed = true;
  }

  private scheduleRecovery(reason: DesktopRecoveryReason): void {
    const elapsedMs = this.lastStartedAtMs === null ? DESKTOP_RECOVERY_MIN_INTERVAL_MS : this.now() - this.lastStartedAtMs;
    const delayMs = Math.max(0, DESKTOP_RECOVERY_MIN_INTERVAL_MS - elapsedMs);
    if (delayMs === 0) {
      this.run(reason);
      return;
    }
    this.pendingRecovery = reason;
    this.recoveryTimer = this.timers.setTimeout(() => {
      this.recoveryTimer = null;
      const pending = this.pendingRecovery;
      this.pendingRecovery = null;
      if (pending) this.run(pending);
    }, delayMs);
  }

  private run(reason: DesktopRegistrationReason): void {
    if (!this.running || this.disposed || this.operation) return;
    this.clearRecoveryTimer();
    this.pendingRecovery = null;
    // Also invalidates any asynchronous binding check notified by the last
    // successful operation. Its owner must check isCurrent before applying it.
    this.contextController?.abort();
    const controller = new AbortController();
    this.contextController = controller;
    const generation = ++this.generation;
    const startedAtMs = this.now();
    const context: DesktopRegistrationContext = {
      signal: controller.signal,
      generation,
      startedAtMs,
      reason,
      isCurrent: () => this.running && !this.disposed && this.generation === generation
        && !controller.signal.aborted && this.now() - startedAtMs < DESKTOP_REGISTRATION_TIMEOUT_MS,
    };
    const operation: RegistrationOperation = { context, controller, timeout: null };
    this.operation = operation;
    this.lastStartedAtMs = startedAtMs;
    this.attempts += 1;
    operation.timeout = this.timers.setTimeout(() => {
      this.finish(operation, false, "registration-timeout");
    }, DESKTOP_REGISTRATION_TIMEOUT_MS);
    this.diagnose("started");
    if (!context.isCurrent()) return;
    // Attach both handlers even if the port ignores abort and settles late.
    // Such settlements cannot alter state or produce unhandled rejections.
    void this.invokeRegistration(context).then(
      success => this.finish(operation, success, success ? null : "registration-rejected"),
      () => this.finish(operation, false, "registration-failed"),
    );
  }

  private async invokeRegistration(context: DesktopRegistrationContext): Promise<boolean> {
    return this.ports.register(context);
  }

  private expireOverdueOperation(): void {
    const operation = this.operation;
    if (operation && this.now() - operation.context.startedAtMs >= DESKTOP_REGISTRATION_TIMEOUT_MS) {
      this.finish(operation, false, "registration-timeout");
    }
  }

  private finish(operation: RegistrationOperation, success: boolean, errorCode: DesktopConnectionError | null): void {
    if (this.operation !== operation || !this.running) return;
    // The event loop can resume with a response before an overdue timer fires.
    if (this.now() - operation.context.startedAtMs >= DESKTOP_REGISTRATION_TIMEOUT_MS) {
      success = false;
      errorCode = "registration-timeout";
    }
    if (operation.timeout !== null) this.timers.clearTimeout(operation.timeout);
    operation.timeout = null;
    this.operation = null;
    if (success) {
      this.pendingRecovery = null;
      this.lastSuccessAtMs = this.now();
      this.lastErrorCode = null;
      this.consecutiveFailures = 0;
      this.successes += 1;
      this.diagnose("succeeded", operation);
      // A notification cannot make a completed registration fail or keep it
      // busy; callers own their separate bounded binding validation.
      if (operation.context.isCurrent()) {
        try { this.ports.onSuccess?.(operation.context); } catch { /* keep heartbeat ownership */ }
      }
      return;
    }
    operation.controller.abort();
    this.lastFailureAtMs = this.now();
    this.lastErrorCode = errorCode;
    this.consecutiveFailures += 1;
    this.failures += 1;
    if (errorCode === "registration-timeout") this.timeouts += 1;
    this.diagnose("failed", operation);
    const pending = this.pendingRecovery;
    this.pendingRecovery = null;
    if (pending) this.scheduleRecovery(pending);
  }

  private clearRecoveryTimer(): void {
    if (this.recoveryTimer !== null) this.timers.clearTimeout(this.recoveryTimer);
    this.recoveryTimer = null;
  }

  private diagnose(event: DesktopConnectionDiagnostic["event"], operation?: RegistrationOperation): void {
    const atMs = this.now();
    const diagnostic: DesktopConnectionDiagnostic = {
      ...this.snapshot(),
      type: "desktop-connection",
      event,
      atMs,
      durationMs: operation ? Math.max(0, atMs - operation.context.startedAtMs) : null,
      successAgeMs: this.lastSuccessAtMs === null ? null : Math.max(0, atMs - this.lastSuccessAtMs),
    };
    // Diagnostics are a fixed metadata whitelist, never the raw port result or
    // exception, and a logger failure cannot prevent heartbeat scheduling.
    try { this.ports.onDiagnostic?.(diagnostic); } catch { /* diagnostics are best effort */ }
  }
}
