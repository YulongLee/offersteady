import type { AudioSourceKind } from "@offersteady/protocol";

export type RealtimeReliabilityState = "STARTING" | "HEALTHY" | "DEGRADED" | "LOST" | "RECOVERING";

export interface RealtimeSourceReliabilitySnapshot {
  readonly sourceKind: AudioSourceKind;
  readonly state: RealtimeReliabilityState;
  readonly startedAtMs: number;
  readonly lastAudioCaptureAt: number | null;
  readonly lastFrameProducedAt: number | null;
  readonly lastFrameSentAt: number | null;
  readonly lastFrameAckAt: number | null;
  readonly lastQwenAppendAt: number | null;
  readonly pendingFrames: number;
  readonly pendingSinceAt: number | null;
  readonly recoveryCount: number;
  readonly lastFailureReason: string | null;
  readonly terminalFailure: boolean;
}

export interface RealtimeReliabilityDecision {
  readonly sourceKind: AudioSourceKind;
  readonly state: RealtimeReliabilityState;
  readonly action: "none" | "recover-source" | "recover-transport";
  readonly reason: string | null;
}

interface MutableSourceReliability {
  sourceKind: AudioSourceKind;
  state: RealtimeReliabilityState;
  startedAtMs: number;
  lastAudioCaptureAt: number | null;
  lastFrameProducedAt: number | null;
  lastFrameSentAt: number | null;
  lastFrameAckAt: number | null;
  lastQwenAppendAt: number | null;
  pendingFrames: number;
  pendingSinceAt: number | null;
  recoveryCount: number;
  lastFailureReason: string | null;
  terminalFailure: boolean;
}

export interface RealtimeReliabilityOptions {
  readonly startupGraceMs?: number;
  readonly degradedCaptureMs?: number;
  readonly lostCaptureMs?: number;
  readonly degradedAckMs?: number;
  readonly lostAckMs?: number;
}

export class RealtimeReliabilityController {
  private readonly sources = new Map<AudioSourceKind, MutableSourceReliability>();
  private readonly startupGraceMs: number;
  private readonly degradedCaptureMs: number;
  private readonly lostCaptureMs: number;
  private readonly degradedAckMs: number;
  private readonly lostAckMs: number;

  constructor(options: RealtimeReliabilityOptions = {}) {
    this.startupGraceMs = options.startupGraceMs ?? 6_000;
    this.degradedCaptureMs = options.degradedCaptureMs ?? 1_000;
    this.lostCaptureMs = options.lostCaptureMs ?? 2_000;
    this.degradedAckMs = options.degradedAckMs ?? 2_000;
    this.lostAckMs = options.lostAckMs ?? 3_000;
  }

  start(sourceKind: AudioSourceKind, nowMs = Date.now()): void {
    this.sources.set(sourceKind, {
      sourceKind,
      state: "STARTING",
      startedAtMs: nowMs,
      lastAudioCaptureAt: null,
      lastFrameProducedAt: null,
      lastFrameSentAt: null,
      lastFrameAckAt: null,
      lastQwenAppendAt: null,
      pendingFrames: 0,
      pendingSinceAt: null,
      recoveryCount: 0,
      lastFailureReason: null,
      terminalFailure: false,
    });
  }

  remove(sourceKind: AudioSourceKind): void {
    this.sources.delete(sourceKind);
  }

  recordAudioCapture(sourceKind: AudioSourceKind, atMs = Date.now()): void {
    const source = this.ensure(sourceKind, atMs);
    source.lastAudioCaptureAt = atMs;
    if (!source.terminalFailure && source.lastFrameAckAt !== null && source.state !== "RECOVERING") {
      source.state = "HEALTHY";
      source.lastFailureReason = null;
    }
  }

  recordFrameProduced(sourceKind: AudioSourceKind, atMs = Date.now()): void {
    const source = this.ensure(sourceKind, atMs);
    source.lastFrameProducedAt = atMs;
  }

  recordFrameSent(sourceKind: AudioSourceKind, atMs = Date.now(), pendingFrames?: number): void {
    const source = this.ensure(sourceKind, atMs);
    source.lastFrameSentAt = atMs;
    if (source.pendingFrames === 0) source.pendingSinceAt = atMs;
    source.pendingFrames = Math.max(1, pendingFrames ?? source.pendingFrames + 1);
  }

  recordFrameAck(sourceKind: AudioSourceKind, atMs = Date.now(), pendingFrames = 0): void {
    const source = this.ensure(sourceKind, atMs);
    if (source.terminalFailure) return;
    source.lastFrameAckAt = atMs;
    source.pendingFrames = Math.max(0, pendingFrames);
    source.pendingSinceAt = source.pendingFrames > 0 ? atMs : null;
    source.state = "HEALTHY";
    source.lastFailureReason = null;
  }

  recordQwenAppend(sourceKind: AudioSourceKind, atMs: number): void {
    if (!Number.isFinite(atMs) || atMs <= 0) return;
    this.ensure(sourceKind, atMs).lastQwenAppendAt = atMs;
  }

  updatePendingFrames(sourceKind: AudioSourceKind, pendingFrames: number): void {
    const nowMs = Date.now();
    const source = this.ensure(sourceKind, nowMs);
    const nextPending = Math.max(0, pendingFrames);
    if (source.pendingFrames === 0 && nextPending > 0) source.pendingSinceAt = nowMs;
    if (nextPending === 0) source.pendingSinceAt = null;
    source.pendingFrames = nextPending;
  }

  markRecovering(sourceKind: AudioSourceKind, reason: string): void {
    const source = this.ensure(sourceKind, Date.now());
    if (source.terminalFailure) return;
    source.state = "RECOVERING";
    source.recoveryCount += 1;
    source.lastFailureReason = reason;
  }

  markTerminalLost(sourceKind: AudioSourceKind, reason: string): void {
    const source = this.ensure(sourceKind, Date.now());
    source.state = "LOST";
    source.pendingFrames = 0;
    source.pendingSinceAt = null;
    source.lastFailureReason = reason;
    source.terminalFailure = true;
  }

  evaluate(nowMs = Date.now()): readonly RealtimeReliabilityDecision[] {
    return [...this.sources.values()].map((source) => {
      if (source.terminalFailure) {
        source.state = "LOST";
        return { sourceKind: source.sourceKind, state: source.state, action: "none", reason: source.lastFailureReason };
      }
      // Recovery is not an exemption from delivery supervision. Once fresh
      // media exists, a recovering channel must still prove ACK progress.
      // Otherwise one healthy channel can leave its sibling stuck forever.
      if (source.pendingFrames > 0 && source.pendingSinceAt !== null) {
        const ackAgeMs = Math.max(0, nowMs - source.pendingSinceAt);
        if (ackAgeMs > this.lostAckMs) {
          source.state = "LOST";
          source.lastFailureReason = "frame-ack-stalled";
          return { sourceKind: source.sourceKind, state: source.state, action: "recover-transport", reason: source.lastFailureReason };
        }
        if (ackAgeMs > this.degradedAckMs) {
          source.state = "DEGRADED";
          source.lastFailureReason = "frame-ack-delayed";
          return { sourceKind: source.sourceKind, state: source.state, action: "none", reason: source.lastFailureReason };
        }
      }
      if (source.state === "RECOVERING") {
        return { sourceKind: source.sourceKind, state: source.state, action: "none", reason: source.lastFailureReason };
      }
      const captureReference = source.lastAudioCaptureAt ?? source.startedAtMs;
      const captureAgeMs = Math.max(0, nowMs - captureReference);
      const insideStartupGrace = source.lastAudioCaptureAt === null && nowMs - source.startedAtMs < this.startupGraceMs;
      if (!insideStartupGrace && captureAgeMs > this.lostCaptureMs) {
        source.state = "LOST";
        source.lastFailureReason = "capture-callback-stalled";
        return { sourceKind: source.sourceKind, state: source.state, action: "recover-source", reason: source.lastFailureReason };
      }
      if (!insideStartupGrace && captureAgeMs > this.degradedCaptureMs) {
        source.state = "DEGRADED";
        source.lastFailureReason = "capture-callback-delayed";
        return { sourceKind: source.sourceKind, state: source.state, action: "none", reason: source.lastFailureReason };
      }
      source.state = source.lastFrameAckAt === null || insideStartupGrace ? "STARTING" : "HEALTHY";
      source.lastFailureReason = null;
      return { sourceKind: source.sourceKind, state: source.state, action: "none", reason: null };
    });
  }

  snapshot(): readonly RealtimeSourceReliabilitySnapshot[] {
    return [...this.sources.values()].map((source) => ({ ...source }));
  }

  private ensure(sourceKind: AudioSourceKind, nowMs: number): MutableSourceReliability {
    const existing = this.sources.get(sourceKind);
    if (existing) return existing;
    this.start(sourceKind, nowMs);
    return this.sources.get(sourceKind)!;
  }
}
