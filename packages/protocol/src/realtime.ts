export const REALTIME_PROTOCOL_VERSION = "2.0" as const;

export type RealtimeAudioChannel = "microphone" | "system";

export interface RealtimeAudioEnvelopeV2 {
  readonly type: "audio-frame";
  readonly deviceId: string;
  readonly sourceId: string;
  readonly sourceKind: RealtimeAudioChannel;
  readonly sequence: number;
  readonly segmentId: string;
  readonly revision: number;
  readonly capturedAtMs: number;
  readonly startedAtMs: number;
  readonly endedAtMs: number;
  readonly durationMs: number;
  readonly codec: "pcm-s16le";
  readonly sampleRateHz: 16000;
  readonly channels: 1 | 2;
  readonly isFinal: boolean;
  readonly traceId: string;
  readonly sentAtMs: number;
  readonly audioBase64: string;
}

export interface RealtimeTransportAckV2 {
  readonly kind: "frame-accepted" | "sequence-gap" | "connection-state" | "degraded";
  readonly payload: Record<string, unknown>;
}

export interface RealtimeTranscriptCursorV2 {
  readonly sessionId: string;
  readonly cursor: number;
  readonly segmentId: string;
  readonly revision: number;
  readonly role: "candidate" | "interviewer";
  readonly isFinal: boolean;
}
