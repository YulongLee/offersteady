import type { AudioFrame, AudioSourceKind } from "@offersteady/protocol";

export class SourceFrameSequencer {
  private readonly nextBySource = new Map<string, number>();

  next(sourceId: string): number {
    const sequence = this.nextBySource.get(sourceId) ?? 0;
    this.nextBySource.set(sourceId, sequence + 1);
    return sequence;
  }
}

export interface CreateFrameInput {
  readonly sessionId: string;
  readonly deviceId: string;
  readonly sourceId: string;
  readonly sourceKind: AudioSourceKind;
  readonly capturedAtMs: number;
  readonly durationMs: number;
  readonly payload: Uint8Array;
}

export const createAudioFrame = (
  sequencer: SourceFrameSequencer,
  input: CreateFrameInput,
): AudioFrame => ({
  ...input,
  sequence: sequencer.next(input.sourceKind),
  codec: "pcm-s16le",
  sampleRateHz: 16_000,
  channels: 1,
});

export class BoundedAudioFrameBuffer {
  private frames: AudioFrame[] = [];
  private byteLength = 0;

  constructor(readonly maximumBytes: number) {
    if (!Number.isInteger(maximumBytes) || maximumBytes <= 0) {
      throw new Error("maximumBytes must be a positive integer");
    }
  }

  push(frame: AudioFrame): readonly AudioFrame[] {
    const dropped: AudioFrame[] = [];
    if (frame.payload.byteLength > this.maximumBytes) return [frame];
    this.frames.push(frame);
    this.byteLength += frame.payload.byteLength;
    while (this.byteLength > this.maximumBytes) {
      const removed = this.frames.shift();
      if (!removed) break;
      this.byteLength -= removed.payload.byteLength;
      dropped.push(removed);
    }
    return dropped;
  }

  acknowledge(sourceId: string, sequence: number): void {
    this.frames = this.frames.filter((frame) => {
      const acknowledged = frame.sourceId === sourceId && frame.sequence <= sequence;
      if (acknowledged) this.byteLength -= frame.payload.byteLength;
      return !acknowledged;
    });
  }

  pending(): readonly AudioFrame[] {
    return [...this.frames];
  }

  clear(): void {
    this.frames = [];
    this.byteLength = 0;
  }
}
