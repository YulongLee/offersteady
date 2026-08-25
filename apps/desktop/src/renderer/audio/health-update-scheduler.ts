export class HealthUpdateScheduler<T> {
  private lastEmissionAtMs = Number.NEGATIVE_INFINITY;
  private pending: T | null = null;
  private timer: ReturnType<typeof setTimeout> | null = null;

  constructor(
    private readonly emit: (value: T) => void,
    private readonly intervalMs = 100,
    private readonly now: () => number = Date.now,
  ) {}

  push(value: T): void {
    this.pending = value;
    const remainingMs = this.intervalMs - (this.now() - this.lastEmissionAtMs);
    if (remainingMs <= 0) {
      this.emitPending();
      return;
    }
    if (this.timer !== null) return;
    this.timer = setTimeout(() => {
      this.timer = null;
      this.emitPending();
    }, remainingMs);
  }

  dispose(): void {
    if (this.timer !== null) clearTimeout(this.timer);
    this.timer = null;
    this.pending = null;
  }

  private emitPending(): void {
    if (this.pending === null) return;
    const value = this.pending;
    this.pending = null;
    this.lastEmissionAtMs = this.now();
    this.emit(value);
  }
}
