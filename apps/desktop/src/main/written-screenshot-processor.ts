export interface WrittenScreenshotJob {
  readonly requestId: string;
  readonly identity: { readonly deviceId: string; readonly manualCode: string };
  readonly bindingKey: string;
  readonly generation: number;
  /** A lease already acquired by an explicit shortcut request. */
  readonly release?: () => void;
}

export interface WrittenScreenshotInspection {
  readonly current: boolean;
  readonly requested: boolean;
}

export type WrittenScreenshotFailureCode =
  | "capture-timeout" | "capture-failed"
  | "upload-timeout" | "upload-failed" | "upload-outcome-unknown"
  | "request-check-failed" | "request-expired" | "queue-full";

export interface WrittenScreenshotFailure {
  readonly stage: "request" | "capture" | "upload";
  readonly code: WrittenScreenshotFailureCode;
  readonly message: string;
}

export interface WrittenScreenshotOutcome {
  readonly status: "uploaded" | "skipped" | "cancelled" | "failed" | "unconfirmed" | "rejected";
  readonly failure?: WrittenScreenshotFailure;
}

export interface WrittenScreenshotPorts<Capture> {
  readonly inspect: (job: WrittenScreenshotJob, signal: AbortSignal) => Promise<WrittenScreenshotInspection>;
  readonly capture: (job: WrittenScreenshotJob, signal: AbortSignal) => Promise<Capture>;
  readonly upload: (job: WrittenScreenshotJob, capture: Capture, signal: AbortSignal) => Promise<void>;
  readonly report: (job: WrittenScreenshotJob, failure: WrittenScreenshotFailure, signal: AbortSignal) => Promise<void>;
  readonly notice: (job: WrittenScreenshotJob, message: string) => void;
  /** Return null while an ordinary capture owns the shared lock; call resume when it releases. */
  readonly acquire: (job: WrittenScreenshotJob) => (() => void) | null;
  readonly settled?: (job: WrittenScreenshotJob, outcome: WrittenScreenshotOutcome) => void;
}

export interface WrittenScreenshotProcessorOptions {
  readonly maxPending?: number;
  readonly captureTimeoutMs?: number;
  readonly uploadTimeoutMs?: number;
  readonly inspectionTimeoutMs?: number;
  readonly reportTimeoutMs?: number;
  readonly queueTimeoutMs?: number;
}

interface Entry {
  readonly key: string;
  readonly recentKey: string;
  readonly job: WrittenScreenshotJob;
  readonly controller: AbortController;
  readonly completion: Promise<WrittenScreenshotOutcome>;
  readonly resolve: (outcome: WrittenScreenshotOutcome) => void;
  readonly queuedAt: number;
  release: (() => void) | null;
  captureStarted: boolean;
  settled: boolean;
}

class OperationTimeout extends Error {}
class OperationCancelled extends Error {}

const failureFor = (stage: "request" | "capture" | "upload", timeout: boolean): WrittenScreenshotFailure => {
  if (stage === "capture") return {
    stage, code: timeout ? "capture-timeout" : "capture-failed",
    message: timeout ? "截屏等待超时，请重试。" : "未能截取当前屏幕，请在助手确认屏幕选择和录制权限后重试。",
  };
  if (stage === "upload") return {
    stage, code: timeout ? "upload-timeout" : "upload-failed",
    message: timeout ? "截图回传超时，请查看网页状态后重试。" : "截图回传失败，请检查连接后重试。",
  };
  return { stage, code: "request-check-failed", message: "暂时无法确认截图请求，请检查助手连接后重试。" };
};

/** Serializes explicit written requests; it never creates requests or retries uploads. */
export class WrittenScreenshotProcessor<Capture> {
  private readonly entries = new Map<string, Entry>();
  private readonly recent = new Map<string, WrittenScreenshotOutcome>();
  private pending: Entry[] = [];
  private active: Entry | null = null;
  private readonly maxPending: number;
  private readonly captureTimeoutMs: number;
  private readonly uploadTimeoutMs: number;
  private readonly inspectionTimeoutMs: number;
  private readonly reportTimeoutMs: number;
  private readonly queueTimeoutMs: number;
  private readonly counters = { enqueued: 0, deduplicated: 0, rejected: 0, captured: 0, uploaded: 0, timedOut: 0, cancelled: 0 };

  constructor(private readonly ports: WrittenScreenshotPorts<Capture>, options: WrittenScreenshotProcessorOptions = {}) {
    this.maxPending = Math.min(4, Math.max(1, options.maxPending ?? 4));
    this.captureTimeoutMs = options.captureTimeoutMs ?? 10_000;
    this.uploadTimeoutMs = options.uploadTimeoutMs ?? 30_000;
    this.inspectionTimeoutMs = options.inspectionTimeoutMs ?? 5_000;
    this.reportTimeoutMs = options.reportTimeoutMs ?? 5_000;
    this.queueTimeoutMs = Math.min(60_000, options.queueTimeoutMs ?? 60_000);
  }

  enqueue(job: WrittenScreenshotJob): {
    readonly status: "accepted" | "duplicate" | "full";
    readonly completion: Promise<WrittenScreenshotOutcome>;
  } {
    const key = JSON.stringify([job.identity.deviceId, job.identity.manualCode, job.bindingKey, job.generation, job.requestId]);
    const recentKey = JSON.stringify([job.identity.deviceId, job.identity.manualCode, job.requestId]);
    const existing = this.entries.get(key);
    const recent = this.recent.get(recentKey);
    if (existing || recent) {
      this.counters.deduplicated++;
      this.releaseSafely(job.release);
      return { status: "duplicate", completion: existing?.completion ?? Promise.resolve(recent!) };
    }
    if (this.pending.length >= this.maxPending) {
      this.counters.rejected++;
      this.releaseSafely(job.release);
      const failure: WrittenScreenshotFailure = { stage: "request", code: "queue-full", message: "截图请求较多，请稍候重试。" };
      this.notice(job, failure.message);
      return { status: "full", completion: Promise.resolve({ status: "rejected", failure }) };
    }
    let resolve!: (outcome: WrittenScreenshotOutcome) => void;
    const completion = new Promise<WrittenScreenshotOutcome>(done => { resolve = done; });
    const entry: Entry = { key, recentKey, job, completion, resolve, queuedAt: Date.now(), controller: new AbortController(), release: job.release ?? null, captureStarted: false, settled: false };
    this.entries.set(key, entry);
    this.pending.push(entry);
    this.counters.enqueued++;
    this.pump();
    return { status: "accepted", completion };
  }

  resume(): void { this.pump(); }

  cancelAll(): number { return this.cancelWhere(() => true); }

  cancelWhere(predicate: (job: WrittenScreenshotJob) => boolean): number {
    const cancelled = this.pending.filter(entry => predicate(entry.job));
    this.pending = this.pending.filter(entry => !cancelled.includes(entry));
    if (this.active && predicate(this.active.job)) cancelled.push(this.active);
    for (const entry of cancelled) {
      entry.controller.abort();
      this.counters.cancelled++;
      this.finish(entry, { status: "cancelled" }, false);
    }
    this.pump();
    return cancelled.length;
  }

  snapshot() {
    return {
      activeRequestId: this.active?.job.requestId ?? null,
      pendingCount: this.pending.length,
      recentCount: this.recent.size,
      counters: { ...this.counters },
    };
  }

  private pump(): void {
    if (this.active) return;
    const entry = this.pending[0];
    if (!entry) return;
    try {
      entry.release ??= this.ports.acquire(entry.job);
    } catch {
      this.pending.shift();
      const failure = failureFor("request", false);
      this.notice(entry.job, failure.message);
      this.finish(entry, { status: "failed", failure });
      return;
    }
    if (!entry.release) return;
    this.pending.shift();
    this.active = entry;
    // run owns all errors, including ports rejecting after their deadline.
    void this.run(entry);
  }

  private isCurrent(entry: Entry): boolean {
    return this.active === entry && !entry.settled && !entry.controller.signal.aborted;
  }

  private async run(entry: Entry): Promise<void> {
    let stage: "request" | "capture" | "upload" = "request";
    try {
      const before = await this.inspect(entry);
      if (!this.isCurrent(entry)) return;
      if (!before.current || !before.requested) {
        this.finish(entry, { status: "skipped" });
        return;
      }
      if (Date.now() - entry.queuedAt >= this.queueTimeoutMs) {
        await this.handleFailure(entry, { stage: "request", code: "request-expired", message: "截图请求等待过久，请重新截屏。" });
        return;
      }
      stage = "capture";
      entry.captureStarted = true;
      this.counters.captured++;
      this.notice(entry.job, "正在截取当前屏幕。");
      const capture = await this.bounded(entry, this.captureTimeoutMs, signal => this.ports.capture(entry.job, signal));
      if (!this.isCurrent(entry)) return;
      stage = "request";
      const after = await this.inspect(entry);
      if (!this.isCurrent(entry)) return;
      if (!after.current || !after.requested) {
        this.finish(entry, { status: "skipped" });
        return;
      }
      stage = "upload";
      await this.bounded(entry, this.uploadTimeoutMs, signal => this.ports.upload(entry.job, capture, signal));
      if (!this.isCurrent(entry)) return;
      this.counters.uploaded++;
      this.notice(entry.job, "截图已回传，请查看网页处理状态。");
      this.finish(entry, { status: "uploaded" });
    } catch (error) {
      if (!this.isCurrent(entry)) return;
      if (error instanceof OperationCancelled) return;
      if (error instanceof OperationTimeout) this.counters.timedOut++;
      const failure = failureFor(stage, error instanceof OperationTimeout);
      await this.handleFailure(entry, failure);
    }
  }

  private inspect(entry: Entry): Promise<WrittenScreenshotInspection> {
    return this.bounded(entry, this.inspectionTimeoutMs, signal => this.ports.inspect(entry.job, signal));
  }

  private async handleFailure(entry: Entry, failure: WrittenScreenshotFailure): Promise<void> {
    // Recheck before reporting: cancellation/accepted uploads must not be overwritten.
    let inspection: WrittenScreenshotInspection | null = null;
    if (failure.stage !== "request" || failure.code === "request-expired") {
      try { inspection = await this.inspect(entry); } catch { /* The result remains unknown. */ }
    }
    if (!this.isCurrent(entry)) return;
    if (inspection && !inspection.current) {
      this.finish(entry, { status: "skipped" });
      return;
    }
    if (failure.stage === "upload" && (!inspection || !inspection.requested)) {
      const unknown: WrittenScreenshotFailure = { stage: "upload", code: "upload-outcome-unknown", message: "截图回传结果尚未确认，请查看网页状态。" };
      this.notice(entry.job, unknown.message);
      this.finish(entry, { status: "unconfirmed", failure: unknown });
      return;
    }
    if (failure.stage === "capture" && inspection && !inspection.requested) {
      this.finish(entry, { status: "skipped" });
      return;
    }
    if (inspection?.current && inspection.requested) {
      try {
        await this.bounded(entry, this.reportTimeoutMs, signal => this.ports.report(entry.job, failure, signal));
      } catch { /* A failed report must not retain the capture lease. */ }
    }
    if (!this.isCurrent(entry)) return;
    this.notice(entry.job, failure.message);
    this.finish(entry, { status: "failed", failure });
  }

  private async bounded<T>(entry: Entry, timeoutMs: number, operation: (signal: AbortSignal) => Promise<T>): Promise<T> {
    const controller = new AbortController();
    const deadlineAt = Date.now() + timeoutMs;
    const checkDeadline = () => {
      if (!this.isCurrent(entry)) throw new OperationCancelled();
      if (Date.now() >= deadlineAt) {
        controller.abort();
        throw new OperationTimeout();
      }
    };
    let timer: ReturnType<typeof setTimeout> | undefined;
    let abort!: () => void;
    const deadline = new Promise<never>((_resolve, reject) => {
      abort = () => { controller.abort(); reject(new OperationCancelled()); };
      entry.controller.signal.addEventListener("abort", abort, { once: true });
      timer = setTimeout(() => { controller.abort(); reject(new OperationTimeout()); }, timeoutMs);
    });
    // Promise.race observes late native rejections even when abort cannot stop native work.
    const work = Promise.resolve().then(() => {
      checkDeadline();
      return operation(controller.signal);
    }).then(value => { checkDeadline(); return value; }, error => { checkDeadline(); throw error; });
    try { return await Promise.race([work, deadline]); }
    finally {
      clearTimeout(timer);
      entry.controller.signal.removeEventListener("abort", abort);
    }
  }

  private finish(entry: Entry, outcome: WrittenScreenshotOutcome, pump = true): void {
    if (entry.settled) return;
    entry.settled = true;
    this.entries.delete(entry.key);
    // A noncanonical request skipped before capture may be explicitly rediscovered later.
    if (entry.captureStarted || outcome.failure?.code === "request-expired") {
      // A temporary binding loss may advance generation; an attempted request must not replay.
      this.recent.set(entry.recentKey, outcome);
      while (this.recent.size > 128) this.recent.delete(this.recent.keys().next().value!);
    }
    if (this.active === entry) this.active = null;
    const release = entry.release;
    entry.release = null;
    this.releaseSafely(release ?? undefined);
    entry.resolve(outcome);
    try { this.ports.settled?.(entry.job, outcome); } catch { /* Notifications cannot retain a lease. */ }
    if (pump) this.pump();
  }

  private releaseSafely(release?: () => void): void {
    try { release?.(); } catch { /* The lease owner controls recovery of its own lock. */ }
  }

  private notice(job: WrittenScreenshotJob, message: string): void {
    try { this.ports.notice(job, message); } catch { /* A missing window must not interrupt capture. */ }
  }
}
