export type MicrophonePermission = "unknown" | "prompt" | "granted" | "denied" | "unavailable";

export interface MicrophonePermissionSnapshot {
  readonly permission: MicrophonePermission;
  readonly pending: boolean;
  readonly source: "os" | "unverified";
}

/** OS consent only. Actual device readability is validated by the media owner. */
export class MicrophonePermissionController {
  private requestInFlight: Promise<MicrophonePermissionSnapshot> | null = null;

  constructor(private readonly options: {
    platform: string;
    readStatus: () => string;
    requestAccess: () => Promise<boolean>;
  }) {}

  snapshot(): MicrophonePermissionSnapshot {
    if (this.options.platform !== "darwin" && this.options.platform !== "win32") {
      return { permission: "unknown", pending: false, source: "unverified" };
    }
    try {
      const status = this.options.readStatus();
      const permission: MicrophonePermission = status === "not-determined" ? "prompt"
        : status === "restricted" ? "denied"
        : status === "granted" || status === "denied" || status === "unknown" ? status : "unknown";
      return { permission, pending: this.requestInFlight !== null, source: "os" };
    } catch {
      return { permission: "unavailable", pending: this.requestInFlight !== null, source: "unverified" };
    }
  }

  request(): Promise<MicrophonePermissionSnapshot> {
    if (this.requestInFlight) return this.requestInFlight;
    const current = this.snapshot();
    if (this.options.platform !== "darwin" || current.permission !== "prompt") return Promise.resolve(current);
    // Keep the original OS promise alive. UI waiting is never an OS refusal.
    const work = Promise.resolve().then(() => this.options.requestAccess()).then(() => this.snapshot());
    const result = work.catch((): MicrophonePermissionSnapshot => ({ permission: "unavailable", pending: false, source: "unverified" }))
      .then(value => ({ ...value, pending: false })).finally(() => {
        if (this.requestInFlight === result) this.requestInFlight = null;
      });
    this.requestInFlight = result;
    return result;
  }
}
