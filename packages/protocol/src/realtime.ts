export const REALTIME_PROTOCOL_VERSION = "2.0" as const;

export type RealtimeAudioChannel = "microphone" | "system";
export type RealtimeTurnState = "speaking" | "tail" | "committing";
export type RealtimeTerminalState = "final" | "incomplete";
export type RealtimeFinalizationReason =
  | "silence"
  | "max-duration"
  | "capture-stop"
  | "source-recovery"
  | "backend-watchdog"
  | "provider-completed"
  | "provider-timeout";

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
  /** Optional commercial endpointing metadata; omitted by legacy companions. */
  readonly turnState?: RealtimeTurnState;
  readonly finalizationReason?: RealtimeFinalizationReason;
  readonly sourceGeneration?: number;
  readonly terminalId?: string;
  readonly traceId: string;
  readonly sentAtMs: number;
  readonly audioBase64: string;
}

export interface RealtimeTransportAckV2 {
  readonly kind: "frame-accepted" | "terminal-accepted" | "sequence-gap" | "connection-state" | "degraded";
  readonly payload: Record<string, unknown>;
}

export interface RealtimeTerminalAcknowledgementV2 {
  readonly kind: "terminal-accepted";
  readonly payload: {
    readonly sourceKind: RealtimeAudioChannel;
    readonly sourceId: string;
    readonly sequence: number;
    readonly segmentId: string;
    readonly revision: number;
    readonly terminalId: string;
    readonly sourceGeneration?: number;
    readonly acceptedAtMs: number;
  };
}

export interface RealtimeTranscriptCursorV2 {
  readonly sessionId: string;
  readonly cursor: number;
  readonly segmentId: string;
  readonly revision: number;
  readonly role: "candidate" | "interviewer";
  readonly isFinal: boolean;
}
