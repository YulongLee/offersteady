export type MicrophonePermissionState = "checking" | "pending" | "not-determined" | "granted" | "denied" | "restricted" | "error";

export interface MicrophonePermissionApi {
  read: () => Promise<string | undefined>;
  request: () => Promise<boolean>;
  openSettings: () => Promise<void>;
}

const normalizeStatus = (value: string | undefined): MicrophonePermissionState =>
  value === "granted" || value === "denied" || value === "restricted" || value === "not-determined" ? value : "error";

/** Permission checks never acquire media, contact the backend, or reset privacy grants. */
export class MicrophonePermissionController {
  private revision = 0;
  private disposed = false;
  private pending: Promise<void> | null = null;

  constructor(private readonly api: MicrophonePermissionApi, private readonly onState: (state: MicrophonePermissionState) => void) {}

  private emit(state: MicrophonePermissionState) {
    if (!this.disposed) this.onState(state);
  }

  async refresh(requestIfUndetermined = false): Promise<void> {
    const revision = ++this.revision;
    try {
      const state = normalizeStatus(await this.api.read());
      if (this.disposed || revision !== this.revision) return;
      this.emit(state === "not-determined" && this.pending ? "pending" : state);
      if (requestIfUndetermined && state === "not-determined") void this.request();
    } catch {
      if (revision === this.revision) this.emit(this.pending ? "pending" : "error");
    }
  }

  request(): Promise<void> {
    if (this.disposed) return Promise.resolve();
    if (this.pending) return this.pending;
    const revision = ++this.revision;
    this.emit("pending");
    this.pending = Promise.resolve().then(() => this.api.request()).then(async () => {
      if (this.disposed) return;
      this.pending = null;
      await this.refresh();
    }, async () => {
      if (this.disposed) return;
      this.pending = null;
      // A focus refresh may already have observed a newer OS grant.
      if (revision !== this.revision) {
        await this.refresh();
        return;
      }
      ++this.revision;
      this.emit("error");
    });
    return this.pending;
  }

  async openSettings(): Promise<void> {
    try { await this.api.openSettings(); } catch { this.emit("error"); }
  }

  dispose() { this.disposed = true; ++this.revision; }
}

export const microphonePermissionCopy: Record<MicrophonePermissionState, string> = {
  checking: "正在检查麦克风权限…",
  pending: "等待你在 macOS 弹窗中允许麦克风，请留意其他窗口后方。等待不会被判定为拒绝。",
  "not-determined": "尚未授权麦克风。请点击申请授权；若没有弹窗，可打开系统设置检查。",
  granted: "麦克风权限已允许。权限检查不会录音。",
  denied: "麦克风权限已拒绝。请在系统设置中允许面试稳伴随程序，再返回检查；若仍无法收音，请完全退出并重新打开助手。",
  restricted: "麦克风访问受系统或管理员限制。请检查设备管理策略，或联系管理员。",
  error: "未能确认麦克风权限，请重新检查；若系统设置没有此应用，请确认安装的是最新版且 macOS 为 14.2 或以上。",
};
