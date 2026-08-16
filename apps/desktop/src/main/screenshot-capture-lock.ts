export interface ScreenshotCaptureLockState {
  readonly locked: boolean;
  readonly message: string;
}

const unlockedMessage = "可以开始新的截屏。";
const lockedMessage = "上一笔截屏仍在处理中，请稍候。";

export class ScreenshotCaptureLock {
  private locked = false;

  tryAcquire(): boolean {
    if (this.locked) return false;
    this.locked = true;
    return true;
  }

  release(): void {
    this.locked = false;
  }

  state(): ScreenshotCaptureLockState {
    return {
      locked: this.locked,
      message: this.locked ? lockedMessage : unlockedMessage,
    };
  }
}
