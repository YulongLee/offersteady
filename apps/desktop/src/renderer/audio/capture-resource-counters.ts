import type { AudioSourceKind } from "@offersteady/protocol";

export interface CaptureResourceCounterSnapshot {
  readonly capturedAtMs: number;
  readonly audioWorkletCallbackCount: number;
  readonly workletPostMessageCount: number;
  readonly audioBytes: number;
  readonly float32ArrayAllocations: number;
  readonly ownedArrayBufferBytes: number;
  readonly activeAudioContexts: number;
  readonly activeAudioNodes: number;
  readonly activeMediaStreamTracks: number;
  readonly activeListeners: number;
  readonly activeTimers: number;
  readonly bySource: Readonly<Record<AudioSourceKind, {
    readonly callbackCount: number;
    readonly postMessageCount: number;
    readonly audioBytes: number;
  }>>;
}

interface MutableSourceCounters {
  callbackCount: number;
  postMessageCount: number;
  audioBytes: number;
}

export class CaptureResourceCounters {
  private readonly sources = new Map<AudioSourceKind, MutableSourceCounters>();
  private float32ArrayAllocations = 0;
  private ownedArrayBufferBytes = 0;
  private activeAudioContexts = 0;
  private activeAudioNodes = 0;
  private activeMediaStreamTracks = 0;
  private activeListeners = 0;
  private activeTimers = 0;

  recordWorkletBatch(sourceKind: AudioSourceKind, input: {
    readonly callbackCount?: number;
    readonly postMessageCount?: number;
    readonly audioBytes: number;
    readonly float32ArrayAllocations?: number;
  }): void {
    const counters = this.source(sourceKind);
    counters.callbackCount += Math.max(0, input.callbackCount ?? 1);
    counters.postMessageCount += Math.max(0, input.postMessageCount ?? 1);
    counters.audioBytes += Math.max(0, input.audioBytes);
    this.float32ArrayAllocations += Math.max(0, input.float32ArrayAllocations ?? 1);
  }

  setOwnedArrayBufferBytes(bytes: number): void { this.ownedArrayBufferBytes = Math.max(0, bytes); }
  addAudioContext(): void { this.activeAudioContexts += 1; }
  removeAudioContext(): void { this.activeAudioContexts = Math.max(0, this.activeAudioContexts - 1); }
  addAudioNodes(count: number): void { this.activeAudioNodes += Math.max(0, count); }
  removeAudioNodes(count: number): void { this.activeAudioNodes = Math.max(0, this.activeAudioNodes - Math.max(0, count)); }
  addMediaTracks(count: number): void { this.activeMediaStreamTracks += Math.max(0, count); }
  removeMediaTracks(count: number): void { this.activeMediaStreamTracks = Math.max(0, this.activeMediaStreamTracks - Math.max(0, count)); }
  addListeners(count: number): void { this.activeListeners += Math.max(0, count); }
  removeListeners(count: number): void { this.activeListeners = Math.max(0, this.activeListeners - Math.max(0, count)); }
  addTimer(): void { this.activeTimers += 1; }
  removeTimer(): void { this.activeTimers = Math.max(0, this.activeTimers - 1); }

  snapshot(nowMs = Date.now()): CaptureResourceCounterSnapshot {
    const microphone = this.source("microphone");
    const system = this.source("system");
    return {
      capturedAtMs: nowMs,
      audioWorkletCallbackCount: microphone.callbackCount + system.callbackCount,
      workletPostMessageCount: microphone.postMessageCount + system.postMessageCount,
      audioBytes: microphone.audioBytes + system.audioBytes,
      float32ArrayAllocations: this.float32ArrayAllocations,
      ownedArrayBufferBytes: this.ownedArrayBufferBytes,
      activeAudioContexts: this.activeAudioContexts,
      activeAudioNodes: this.activeAudioNodes,
      activeMediaStreamTracks: this.activeMediaStreamTracks,
      activeListeners: this.activeListeners,
      activeTimers: this.activeTimers,
      bySource: {
        microphone: { ...microphone },
        system: { ...system },
      },
    };
  }

  private source(sourceKind: AudioSourceKind): MutableSourceCounters {
    const existing = this.sources.get(sourceKind);
    if (existing) return existing;
    const counters = { callbackCount: 0, postMessageCount: 0, audioBytes: 0 };
    this.sources.set(sourceKind, counters);
    return counters;
  }
}
