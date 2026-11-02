export const RESTORE_WINDOW_SHORTCUT = "CommandOrControl+Shift+H";

interface WindowVisibilitySurfaces {
  readonly hideWindow: () => void;
  readonly showWindow: () => void;
  readonly skipTaskbar: (skip: boolean) => void;
  readonly setTrayTransparent: (transparent: boolean) => void;
  readonly hideDock?: () => void;
  readonly showDock?: () => void | Promise<void>;
  readonly now?: () => number;
}

/** Visibility owns UI surfaces only, never capture, binding or device identity. */
export class CompanionWindowVisibility {
  private hidden = false;
  private disposed = false;
  private generation = 0;
  private dockTimer: ReturnType<typeof setTimeout> | null = null;
  private lastDockHideAt = -Infinity;

  constructor(private readonly surfaces: WindowVisibilitySurfaces) {}

  isHidden() { return this.hidden; }

  showOnReady(show: () => void) {
    if (!this.disposed && !this.hidden) show();
  }

  hide() {
    if (this.disposed) return;
    this.hidden = true;
    ++this.generation;
    this.cancelDockTimer();
    this.surfaces.hideWindow();
    this.surfaces.skipTaskbar(true);
    this.surfaces.setTrayTransparent(true);
    this.queueDockHide();
  }

  restore() {
    if (this.disposed) return;
    this.hidden = false;
    const generation = ++this.generation;
    this.cancelDockTimer();
    this.surfaces.showWindow();
    this.surfaces.skipTaskbar(false);
    // A native icon failure must never prevent reopening the window.
    try { this.surfaces.setTrayTransparent(false); } catch { /* The visible window remains the recovery surface. */ }
    // A previous async show can settle after a newer hide. Reapply only the
    // latest intent, respecting Dock.hide's repeated-call timing limitation.
    if (this.surfaces.showDock) {
      void Promise.resolve().then(() => {
        if (!this.disposed && !this.hidden && generation === this.generation) return this.surfaces.showDock?.();
      }).then(() => {
        if (!this.disposed && this.hidden) this.queueDockHide();
      }).catch(() => undefined);
    }
  }

  dispose() {
    this.disposed = true;
    ++this.generation;
    this.cancelDockTimer();
  }

  private cancelDockTimer() {
    if (this.dockTimer !== null) clearTimeout(this.dockTimer);
    this.dockTimer = null;
  }

  private queueDockHide() {
    if (!this.surfaces.hideDock || this.disposed || !this.hidden) return;
    this.cancelDockTimer();
    const generation = this.generation;
    const delay = Math.max(0, 1100 - ((this.surfaces.now?.() ?? Date.now()) - this.lastDockHideAt));
    const hide = () => {
      this.dockTimer = null;
      if (this.disposed || !this.hidden || generation !== this.generation) return;
      this.lastDockHideAt = this.surfaces.now?.() ?? Date.now();
      try { this.surfaces.hideDock?.(); } catch { /* Window/app reopening remains available. */ }
    };
    if (delay === 0) hide();
    else this.dockTimer = setTimeout(hide, delay);
  }
}
