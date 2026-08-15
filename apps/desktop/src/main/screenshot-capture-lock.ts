export interface ScreenshotCaptureLockState {
  readonly locked: boolean;
  readonly message: string;
}

const unlockedMessage = "可以开始新的截屏。";
const lockedMessage = "当前截屏尚未取消，请先点击“取消当前截屏”。";

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
