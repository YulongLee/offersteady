import type { AudioPermission } from "@offersteady/protocol";
import { deviceStatusFingerprint } from "./device-status-publish-gate";

export interface MicrophonePermissionSnapshot {
  readonly permission: AudioPermission | "unavailable";
  readonly pending: boolean;
  readonly source: "os" | "unverified" | "media";
}

const permissions = new Set<MicrophonePermissionSnapshot["permission"]>(["unknown", "prompt", "granted", "denied", "unavailable"]);
const unknown = (): MicrophonePermissionSnapshot => ({ permission: "unknown", pending: false, source: "unverified" });
export const normalizeMicrophonePermission = (value: unknown): MicrophonePermissionSnapshot => {
  if (!value || typeof value !== "object") return unknown();
  const candidate = value as Record<string, unknown>;
  if (!permissions.has(candidate.permission as MicrophonePermissionSnapshot["permission"])) return unknown();
  return {
    permission: candidate.permission as MicrophonePermissionSnapshot["permission"],
    pending: candidate.pending === true && (candidate.permission === "unknown" || candidate.permission === "prompt"),
    source: candidate.source === "os" ? "os" : "unverified",
  };
};

export const microphonePermissionFailure = (error: unknown): MicrophonePermissionSnapshot => ({
  permission: error instanceof Error && ["NotAllowedError", "SecurityError"].includes(error.name) ? "denied"
    : error instanceof Error && ["NotFoundError", "NotReadableError", "OverconstrainedError", "AbortError"].includes(error.name)
      ? "unavailable" : "unknown",
  pending: false, source: "media",
});

/** Explicit local check only. The probe owns and stops every returned track, including late results. */
export const probeMicrophonePermission = async (
  mediaDevices: Pick<MediaDevices, "getUserMedia">,
  sourceId = "default",
): Promise<MicrophonePermissionSnapshot> => {
  let stream: MediaStream | undefined;
  try {
    stream = await mediaDevices.getUserMedia({
      audio: sourceId && sourceId !== "default" ? { deviceId: { exact: sourceId } } : true,
      video: false,
    });
    return { permission: stream.getAudioTracks().length > 0 ? "granted" : "unavailable", pending: false, source: "media" };
  } catch (error) {
    return microphonePermissionFailure(error);
  } finally {
    stream?.getTracks().forEach(track => track.stop());
  }
};

interface PermissionOptions {
  readonly read: () => Promise<unknown>;
  readonly request: () => Promise<unknown>;
  readonly probe: () => Promise<MicrophonePermissionSnapshot>;
  readonly onChange: (snapshot: MicrophonePermissionSnapshot) => void;
  readonly waitMs?: number;
}

/** A bounded UI wait observes one real operation; it never turns timeout into denial. */
export class MicrophonePermissionCoordinator {
  private snapshot = unknown();
  private flight: Promise<MicrophonePermissionSnapshot> | null = null;
  private waiting: Promise<MicrophonePermissionSnapshot> | null = null;
  private timer: ReturnType<typeof setTimeout> | undefined;
  private finishWait: ((snapshot: MicrophonePermissionSnapshot) => void) | undefined;
  private refreshFlight: Promise<MicrophonePermissionSnapshot> | null = null;
  private refreshTimer: ReturnType<typeof setTimeout> | undefined;
  private finishRefresh: ((snapshot: MicrophonePermissionSnapshot) => void) | undefined;
  private revision = 0;
  private disposed = false;
  private phase: "read" | "request" | "probe" | null = null;

  constructor(private readonly options: PermissionOptions) {}

  private publish(snapshot: MicrophonePermissionSnapshot) {
    if (this.disposed) return;
    const previous = this.snapshot;
    this.snapshot = snapshot;
    if (previous.permission !== snapshot.permission || previous.pending !== snapshot.pending || previous.source !== snapshot.source) {
      this.options.onChange(snapshot);
    }
  }

  check(options: { request?: boolean; probe?: boolean } = {}): Promise<MicrophonePermissionSnapshot> {
    if (this.disposed) return Promise.resolve(this.snapshot);
    if (this.flight) {
      return this.timer === undefined ? this.refreshPending(options) : this.waiting ?? this.flight;
    }
    const revision = ++this.revision;
    this.publish({ ...this.snapshot, pending: true });
    this.phase = "read";
    const operation = (async () => {
      let result: MicrophonePermissionSnapshot;
      try {
        result = normalizeMicrophonePermission(await this.options.read());
        if (this.disposed || revision !== this.revision) return this.snapshot;
        if (options.request && !result.pending && (result.permission === "prompt" || result.permission === "unknown")) {
          this.phase = "request";
          result = normalizeMicrophonePermission(await this.options.request());
          if (this.disposed || revision !== this.revision) return this.snapshot;
        }
        if (options.probe && !result.pending && result.permission !== "denied") {
          this.phase = "probe";
          result = await this.options.probe();
        }
        if (result.permission === "unknown" && !result.pending && this.snapshot.source === "media") {
          result = { ...this.snapshot, pending: false };
        }
      } catch {
        result = unknown();
      }
      if (!this.disposed && revision === this.revision) {
        ++this.revision;
        this.publish(result);
      }
      return this.snapshot;
    })();
    this.flight = operation;
    let finishWait!: (snapshot: MicrophonePermissionSnapshot) => void;
    const waiting = new Promise<MicrophonePermissionSnapshot>(resolve => { finishWait = resolve; });
    this.finishWait = finishWait;
    this.waiting = waiting;
    this.timer = setTimeout(() => {
      this.timer = undefined;
      finishWait(this.snapshot);
    }, this.options.waitMs ?? 2_500);
    void operation.finally(() => {
      if (this.flight !== operation) return;
      clearTimeout(this.timer);
      this.timer = undefined;
      this.flight = null;
      this.phase = null;
      this.waiting = null;
      this.finishWait = undefined;
      finishWait(this.snapshot);
    });
    return waiting;
  }

  private detachWait() {
    clearTimeout(this.timer);
    this.timer = undefined;
    this.finishWait?.(this.snapshot);
    this.finishWait = undefined;
    this.flight = null;
    this.waiting = null;
    this.phase = null;
  }

  private detachRefresh() {
    clearTimeout(this.refreshTimer);
    this.refreshTimer = undefined;
    this.finishRefresh?.(this.snapshot);
    this.finishRefresh = undefined;
    this.refreshFlight = null;
  }

  /** A user/focus refresh may read current OS consent while an older native dialog remains pending. */
  private refreshPending(options: { request?: boolean; probe?: boolean }): Promise<MicrophonePermissionSnapshot> {
    if (this.refreshFlight) return this.refreshFlight;
    const revision = this.revision;
    const work = (async () => {
      let result: MicrophonePermissionSnapshot;
      try { result = normalizeMicrophonePermission(await this.options.read()); } catch { return this.snapshot; }
      if (this.disposed || revision !== this.revision) return this.snapshot;
      if (this.phase === "probe" && result.permission === "granted") {
        this.publish({ ...result, pending: true });
        return this.snapshot;
      }
      if (result.permission === "granted" || result.permission === "denied"
        || options.request && !result.pending && this.phase === "read") {
        ++this.revision;
        this.publish(result);
        this.detachWait();
        if (options.probe && result.permission !== "denied" || options.request && (result.permission === "unknown" || result.permission === "prompt")) {
          return this.check(options);
        }
      }
      // Unknown/pending does not retire the original native promise's late result.
      return this.snapshot;
    })();
    const waiting = new Promise<MicrophonePermissionSnapshot>(resolve => { this.finishRefresh = resolve; });
    this.refreshFlight = waiting;
    this.refreshTimer = setTimeout(() => {
      this.refreshTimer = undefined;
      this.finishRefresh?.(this.snapshot);
    }, this.options.waitMs ?? 2_500);
    void work.finally(() => {
      if (this.refreshFlight !== waiting) return;
      this.finishRefresh?.(this.snapshot);
      this.detachRefresh();
    });
    return waiting;
  }

  /** Real acquisition/denial is newer evidence than an old pending permission request. */
  record(permission: MicrophonePermissionSnapshot["permission"]) {
    ++this.revision;
    this.publish({ permission, pending: false, source: "media" });
    this.detachWait();
    this.detachRefresh();
  }

  dispose() {
    this.disposed = true;
    ++this.revision;
    this.detachWait();
    this.detachRefresh();
  }
}

/** Serial latest-value writes; failure stays pending until an existing control cycle retries. */
export class CapabilityRegistrationQueue<T> {
  private desired: { value: T; fingerprint: string } | null = null;
  private lastSuccessful: string | null = null;
  private flight: Promise<void> | null = null;
  private disposed = false;

  constructor(private readonly send: (value: T) => Promise<boolean>) {}

  markSuccessful(value: T) { this.lastSuccessful = deviceStatusFingerprint(value); }

  submit(value: T): Promise<void> {
    if (this.disposed) return Promise.resolve();
    this.desired = { value, fingerprint: deviceStatusFingerprint(value) };
    return this.flush();
  }

  flush(): Promise<void> {
    if (this.disposed || !this.desired || this.desired.fingerprint === this.lastSuccessful) return Promise.resolve();
    if (this.flight) return this.flight;
    const run = (async () => {
      while (!this.disposed && this.desired && this.desired.fingerprint !== this.lastSuccessful) {
        const current = this.desired;
        let succeeded = false;
        try { succeeded = await this.send(current.value); } catch { /* Existing cycle retries. */ }
        if (this.disposed) return;
        if (!succeeded) return;
        this.lastSuccessful = current.fingerprint;
      }
    })();
    this.flight = run;
    void run.finally(() => { if (this.flight === run) this.flight = null; });
    return run;
  }

  dispose() { this.disposed = true; this.desired = null; }
}
