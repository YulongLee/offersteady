export interface ScreenshotCaptureLockState {
  readonly locked: boolean;
  readonly message: string;
}

const unlockedMessage = "可以开始新的截屏。";
const lockedMessage = "上一笔截屏仍在处理中，请稍候。";

export class ScreenshotCaptureLock {
  private locked = false;
  private generation = 0;
  private owner: number | null = null;

  tryAcquire(): boolean {
    if (this.locked) return false;
    this.locked = true;
    this.owner = ++this.generation;
    return true;
  }

  ownerToken(): number | null { return this.owner; }

  release(expectedOwner?: number | null): boolean {
    if (expectedOwner !== undefined && expectedOwner !== this.owner) return false;
    this.locked = false;
    this.owner = null;
    return true;
  }

  state(): ScreenshotCaptureLockState {
    return {
      locked: this.locked,
      message: this.locked ? lockedMessage : unlockedMessage,
    };
  }
}
