/** Holds a short renewable lease only for a currently verified live written binding. */
export class WrittenSessionAwakeGuard {
  private blocker: number | null = null;
  private timer: ReturnType<typeof setTimeout> | null = null;
  private disposed = false;
  constructor(private readonly ports: { start: () => number; stop: (id: number) => void }) {}
  refresh(eligible: boolean): void {
    if (this.timer !== null) clearTimeout(this.timer);
    this.timer = null;
    if (this.disposed || !eligible) { this.release(); return; }
    if (this.blocker === null) {
      try { this.blocker = this.ports.start(); } catch { return; }
    }
    // A stalled renderer or lost binding cannot leave an indefinite power lease.
    this.timer = setTimeout(() => { this.timer = null; this.release(); }, 45_000);
  }
  dispose(): void { this.disposed = true; this.refresh(false); }
  private release(): void {
    const id = this.blocker; this.blocker = null;
    if (id !== null) { try { this.ports.stop(id); } catch { /* An expired OS lease is already inactive. */ } }
  }
}
