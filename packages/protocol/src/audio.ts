export const PROTOCOL_VERSION = "1.0.0" as const;

export type DesktopPlatform = "windows" | "macos" | "unsupported";
export type DesktopArchitecture = "arm64" | "x64" | "universal" | "unknown";

export type AudioPermission = "unknown" | "prompt" | "granted" | "denied";

export type AudioSourceKind = "microphone" | "system";
export type InterviewInputMode = "dual-channel-audio" | "manual";
export type AudioSourceHealthState =
  | "unknown"
  | "unsupported"
  | "permission-required"
  | "receiving"
  | "silent"
  | "unavailable"
  | "permission-denied"
  | "reconnecting"
  | "error";

export type DesktopRuntimeStage =
  | "backend-unreachable"
  | "registered"
  | "bound"
  | "live"
  | "publishing"
  | "transcribing"
  | "web-visible"
  | "degraded"
  | "failed";

export type AudioSourceHealthStage =
  | "unsupported"
  | "permission-required"
  | "permission-denied"
  | "stream-opened"
  | "track-live"
  | "signal-detected"
  | "frames-produced"
  | "frames-published"
  | "asr-accepted"
  | "failed";

export interface StartInterviewCommand {
  readonly id: string;
  readonly idempotencyKey: string;
  readonly sessionId: string;
  readonly requestedByUserId: string;
  readonly inputMode: InterviewInputMode;
  readonly sourceIds: readonly string[];
}

export interface StartInterviewResult {
  readonly sessionId: string;
  readonly status: "active";
  readonly captureState: "capturing" | "ready";
  readonly startedAtMs: number;
}

export type CaptureState =
  | "not-connected"
  | "permission-required"
  | "ready"
  | "capturing"
  | "paused"
  | "reconnecting"
  | "error";

export interface CompanionCapabilities {
  readonly protocolVersion: string;
  readonly appVersion: string;
  readonly platform: DesktopPlatform;
  readonly architecture?: DesktopArchitecture;
  readonly platformVersion: string;
  readonly microphone: AudioPermission;
  readonly systemAudio: AudioPermission;
  readonly availableSources: readonly AudioSourceDescriptor[];
}

export interface AudioSourceDescriptor {
  readonly id: string;
  readonly kind: AudioSourceKind;
  readonly label: string;
  readonly available: boolean;
}

export interface AudioFrame {
  readonly sessionId: string;
  readonly deviceId: string;
  readonly sourceId: string;
  readonly sourceKind: AudioSourceKind;
  readonly sequence: number;
  readonly capturedAtMs: number;
  readonly durationMs: number;
  readonly codec: "opus" | "pcm-s16le";
  readonly sampleRateHz: number;
  readonly channels: 1 | 2;
  readonly payload: Uint8Array;
}

export interface CompanionDeviceStatus {
  readonly deviceId: string;
  readonly displayName: string;
  readonly captureState: CaptureState;
  readonly connected: boolean;
  readonly activeSourceIds: readonly string[];
  readonly capabilities: CompanionCapabilities;
  readonly sourceHealth?: readonly AudioSourceHealth[];
  readonly embeddedWorkspace?: EmbeddedWorkspaceConfig;
  readonly lastSeenAtMs: number;
  readonly errorCode?: CompanionErrorCode;
}

export interface AudioSourceHealth {
  readonly sourceId: string;
  readonly sourceKind: AudioSourceKind;
  readonly label: string;
  readonly state: AudioSourceHealthState;
  readonly stage?: AudioSourceHealthStage;
  readonly level: number;
  readonly lastSignalAtMs?: number;
  readonly frameCount?: number;
  readonly lastFrameAtMs?: number;
  readonly backendFrameCount?: number;
  readonly lastBackendFrameAtMs?: number;
  readonly errorCode?: CompanionErrorCode | "silent-source";
}

export interface DesktopRuntimeSourceReceipt {
  readonly sourceKind: AudioSourceKind | "mixed";
  readonly sourceId: string;
  readonly frameCount: number;
  readonly lastFrameAtMs: number;
  readonly lastSequence: number;
  readonly lastAsrStatus: "pending" | "accepted" | "failed";
  readonly lastErrorCode?: string;
}

export interface RealtimeStageTiming {
  readonly traceId?: string;
  readonly captureToSendMs?: number;
  readonly sendToIngestMs?: number;
  readonly captureToIngestMs?: number;
  readonly queueWaitMs?: number;
  readonly asrTtftMs?: number;
  readonly finalTranscriptMs?: number;
  readonly backendPushMs?: number;
  readonly captureToPublishMs?: number;
  readonly frontendRenderMs?: number;
}

export interface RealtimeRuntimeCounters {
  readonly queueDepth: number;
  readonly droppedPartialUpdates: number;
  readonly connectionRecreations: number;
  readonly emptyResultsSuppressed: number;
  readonly phantomResultsSuppressed: number;
  readonly repetitiveResultsSuppressed: number;
  readonly duplicateResultsSuppressed: number;
  readonly fillerResultsSuppressed: number;
  readonly chunksProduced: number;
  readonly chunksUploaded: number;
  readonly serializedAudioBytes: number;
}

export interface RealtimeRuntimePerformance {
  readonly latestBySource: Partial<Record<AudioSourceKind, RealtimeStageTiming>>;
  readonly countersBySource: Partial<Record<AudioSourceKind, RealtimeRuntimeCounters>>;
}

export interface DesktopRuntimeStatus {
  readonly stage: DesktopRuntimeStage;
  readonly backendReachable: boolean;
  readonly deviceRegistered: boolean;
  readonly machineCodeBound: boolean;
  readonly sessionLive: boolean;
  readonly manualCode?: string;
  readonly deviceId?: string;
  readonly sessionId?: string;
  readonly sessionStatus?: "preparing" | "live" | "ended" | "missing" | "unknown" | string;
  readonly sourceHealth: readonly AudioSourceHealth[];
  readonly frameReceipts: readonly DesktopRuntimeSourceReceipt[];
  readonly transcriptCount: number;
  readonly questionCandidateCount: number;
  readonly lastErrorCode?: string;
  readonly anomalyReasons?: readonly string[];
  readonly dominantBottleneck?: string;
  readonly performance?: RealtimeRuntimePerformance;
  readonly updatedAtMs: number;
}

export interface EmbeddedWorkspaceConfig {
  readonly url: string;
  readonly fallbackUrl?: string;
  readonly openInExternalBrowser: boolean;
}

export type CompanionErrorCode =
  | "permission-denied"
  | "source-unavailable"
  | "adapter-required"
  | "backend-mismatch"
  | "publisher-create-failed"
  | "publisher-websocket-failed"
  | "asr-failed"
  | "incompatible-version"
  | "network-unavailable"
  | "audio-gap"
  | "unknown";

export type CompanionCommand =
  | { readonly id: string; readonly type: "start"; readonly sourceIds: readonly string[] }
  | { readonly id: string; readonly type: "pause" }
  | { readonly id: string; readonly type: "resume" }
  | { readonly id: string; readonly type: "stop" }
  | { readonly id: string; readonly type: "disconnect" };

export interface BindingTokenRequest {
  readonly sessionId: string;
  readonly requestedByUserId: string;
}

export interface BindingToken {
  readonly token: string;
  readonly sessionId: string;
  readonly expiresAtMs: number;
  readonly deepLink: string;
  readonly manualCode: string;
}

export interface DesktopBindingExchangeRequest {
  readonly tokenOrCode: string;
  readonly sessionId: string;
  readonly userId: string;
  readonly deviceId: string;
  readonly displayName: string;
  readonly capabilities: CompanionCapabilities;
}

export interface DesktopBindingExchangeResult {
  readonly deviceCredential: string;
  readonly expiresAtMs: number;
  readonly deviceStatus: CompanionDeviceStatus;
}
