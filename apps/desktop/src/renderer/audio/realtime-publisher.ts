import type { AudioSourceHealth, AudioSourceKind, RealtimeFinalizationReason, RealtimeTurnState } from "@offersteady/protocol";

import { BoundedAudioFrameBuffer, createAudioFrame, SourceFrameSequencer } from "./audio-frame-buffer";
import { MicrophoneAudioAdapter, SystemAudioAdapter, describeMediaError, type OpenAudioSource } from "./audio-source-adapter";
import { calculateRms } from "./signal-diagnostics";
import { MultiplexedRealtimeTransport } from "./multiplexed-realtime-transport";
import { HealthUpdateScheduler } from "./health-update-scheduler";
import { CaptureResourceCounters, type CaptureResourceCounterSnapshot } from "./capture-resource-counters";
import {
  RealtimeReliabilityController,
  type RealtimeSourceReliabilitySnapshot,
} from "./realtime-reliability";
import { RealtimeTransportDiagnostics } from "./realtime-transport-diagnostics";
import { FreshTransportAckGate, ReplacementPublisherBudget } from "./publisher-recovery-policy";
import { SerializedLatestSourceSwitch } from "./audio-device-hot-switch";

interface DesktopBinding {
  readonly sessionId: string;
  readonly ownerUserId: string;
  readonly deviceId: string;
  readonly manualCode: string;
  readonly displayName: string;
}

interface PublisherTokenResponse {
  readonly publisherId: string;
  readonly token: string;
}

interface PublisherSocketEvent {
  readonly kind?: string;
  readonly payload?: Record<string, unknown>;
}

interface HealthSnapshot extends AudioSourceHealth {
  readonly active: boolean;
}

interface RealtimePublisherCallbacks {
  readonly onHealth: (health: readonly AudioSourceHealth[]) => void;
  readonly onCaptureState: (state: "capturing" | "permission-required" | "reconnecting" | "error") => void;
  readonly onFailure: (message: string) => void;
  readonly onServerEvent?: (event: { readonly kind?: string; readonly payload?: Record<string, unknown> }) => void;
  readonly onReliability?: (snapshot: DesktopRealtimeReliabilitySnapshot) => void;
}

interface RealtimePublisherOptions extends RealtimePublisherCallbacks {
  readonly apiBaseUrl: string;
  readonly binding: DesktopBinding;
  readonly microphoneId: string;
  readonly systemAudioId: string;
  readonly endpointingMode?: EndpointingMode;
  readonly fetchImpl?: typeof fetch;
  readonly diagnosticAudioChannels?: readonly AudioSourceKind[];
}

export const sessionCapturePermissionPolicy = {
  requestPermissionOnSessionStart: false,
  systemAudioCapture: "electron-display-loopback",
  captureOwner: "electron-single-owner",
} as const;

export const desktopCaptureArchitecture = "electron-single-owner" as const;

export const productionAudioTransportPolicy = {
  protocol: "websocket-v2",
  automaticLegacyHttpFallback: false,
} as const;

interface RuntimeHandle {
  readonly stop: () => Promise<void>;
}

interface WebAudioSourceRuntime extends RuntimeHandle {
  readonly sourceId: string;
  readonly sourceKind: AudioSourceKind;
  readonly label: string;
  readonly media: OpenAudioSource;
  readonly context: AudioContext;
  readonly processor: AudioNode;
  readonly sink: GainNode;
  readonly node: MediaStreamAudioSourceNode;
}

interface SourceStartInput {
  readonly sourceKind: AudioSourceKind;
  readonly sourceId: string;
  readonly open: () => Promise<OpenAudioSource>;
}

interface SegmentSnapshot {
  readonly sequence: number;
  readonly segmentId: string;
  readonly revision: number;
  readonly capturedAtMs: number;
  readonly startedAtMs: number;
  readonly vadTriggeredAtMs: number;
  readonly speechConfirmedAtMs: number;
  readonly endedAtMs: number;
  readonly durationMs: number;
  readonly isFinal: boolean;
  readonly turnState: RealtimeTurnState;
  readonly finalizationReason?: RealtimeFinalizationReason;
  readonly sourceGeneration: number;
  readonly terminalId?: string;
  readonly payload: Uint8Array;
}

interface CaptureBatchTiming {
  readonly audioWorkletOutputAtMs: number;
  readonly rendererReceiveAtMs: number;
  readonly workletCallbackCount: number;
  readonly workletPostMessageCount: number;
  readonly float32ArrayAllocations: number;
}

export interface DesktopRealtimeReliabilitySnapshot {
  readonly capturedAtMs: number;
  readonly sessionId: string;
  readonly sources: readonly RealtimeSourceReliabilitySnapshot[];
  readonly resources: CaptureResourceCounterSnapshot;
}

export type EndpointingMode = "legacy-threshold" | "commercial-adaptive";
export type SpeechTurnLifecycle = "idle" | RealtimeTurnState | "final" | "incomplete";

export interface SpeechEndpointingConfig {
  readonly mode: EndpointingMode;
  readonly interimIntervalMs: number;
  readonly minimumSpeechMs: number;
  readonly maximumTurnMs: number;
  readonly microphoneTailMs: number;
  readonly systemTailMs: number;
}

const MICROPHONE_SPEECH_START_THRESHOLD = 0.003;
const MICROPHONE_SPEECH_CONTINUE_THRESHOLD = 0.0018;
const SYSTEM_SPEECH_START_THRESHOLD = 0.0008;
const SYSTEM_SPEECH_CONTINUE_THRESHOLD = 0.0005;
const INTERIM_INTERVAL_MS = 100;
const MICROPHONE_SILENCE_FINALIZE_MS = 500;
const SYSTEM_SILENCE_FINALIZE_MS = 500;
const MAX_SEGMENT_DURATION_MS = 30_000;
const MIN_EMIT_SPEECH_MS = 60;
const PRE_SPEECH_BUFFER_LIMIT = 4;
const MICROPHONE_TURN_PEAK_RELEASE_RATIO = 0.15;

interface SourceVadProfile {
  readonly startFloor: number;
  readonly startCeiling: number;
  readonly continuationFloor: number;
  readonly continuationCeiling: number;
  readonly startNoiseMultiplier: number;
  readonly continuationNoiseMultiplier: number;
  readonly attackMs: number;
  readonly minimumSpeechMs: number;
  readonly silenceMs: number;
}

const MICROPHONE_VAD_PROFILE: SourceVadProfile = {
  startFloor: 0.0012,
  startCeiling: 0.012,
  continuationFloor: 0.0011,
  continuationCeiling: 0.008,
  startNoiseMultiplier: 3.2,
  continuationNoiseMultiplier: 2,
  attackMs: 20,
  minimumSpeechMs: 60,
  silenceMs: MICROPHONE_SILENCE_FINALIZE_MS,
};

const SYSTEM_VAD_PROFILE: SourceVadProfile = {
  // Keep the floor low enough for quiet meeting audio, English initials and
  // short numbers. A short attack window rejects one-frame digital noise.
  startFloor: 0.001,
  startCeiling: 0.004,
  continuationFloor: SYSTEM_SPEECH_CONTINUE_THRESHOLD,
  continuationCeiling: 0.0025,
  startNoiseMultiplier: 3.2,
  continuationNoiseMultiplier: 2,
  attackMs: 40,
  minimumSpeechMs: 60,
  silenceMs: SYSTEM_SILENCE_FINALIZE_MS,
};

export const commercialSpeechEndpointingDefaults: SpeechEndpointingConfig = {
  mode: "commercial-adaptive",
  interimIntervalMs: INTERIM_INTERVAL_MS,
  minimumSpeechMs: MIN_EMIT_SPEECH_MS,
  maximumTurnMs: 12_000,
  microphoneTailMs: MICROPHONE_SILENCE_FINALIZE_MS,
  systemTailMs: SYSTEM_SILENCE_FINALIZE_MS,
};
const MAX_PENDING_AUDIO_BYTES = 256_000;
const MEDIA_OPEN_TIMEOUT_MS = 6500;
const SYSTEM_RECOVERY_CHECK_MS = 2_000;
const SYSTEM_CALLBACK_STALL_MS = 4_000;
const SYSTEM_RECOVERY_STARTUP_GRACE_MS = 6_000;
const SYSTEM_SILENCE_RECOVERY_DELAYS_MS = [30_000, 120_000, 300_000] as const;
const REPLACEMENT_PUBLISHER_ACK_TIMEOUT_MS = 4_000;
const MAX_REPLACEMENT_PUBLISHER_ATTEMPTS = 3;

export type SystemAudioRecoveryReason =
  | "track-ended"
  | "track-muted"
  | "audio-context-not-running"
  | "audio-callback-stalled"
  | "system-signal-stalled"
  | "watchdog-capture-lost";

type AudioSourceRecoveryReason = SystemAudioRecoveryReason | "device-change";

interface SystemAudioRecoverySnapshot {
  readonly nowMs: number;
  readonly openedAtMs: number;
  readonly lastProcessAtMs: number;
  readonly lastSignalAtMs: number | null;
  readonly lastRecoveryAtMs: number | null;
  readonly recoveryAttempt: number;
  readonly trackReadyState: MediaStreamTrackState;
  readonly trackMuted: boolean;
  readonly contextState: string;
}

export const systemAudioRecoveryReason = (snapshot: SystemAudioRecoverySnapshot): SystemAudioRecoveryReason | null => {
  if (snapshot.trackReadyState === "ended") return "track-ended";
  const startupComplete = snapshot.nowMs - snapshot.openedAtMs >= SYSTEM_RECOVERY_STARTUP_GRACE_MS;
  if (!startupComplete) return null;
  if (snapshot.trackMuted) return "track-muted";
  if (snapshot.contextState !== "running") return "audio-context-not-running";
  if (
    snapshot.nowMs - snapshot.lastProcessAtMs >= SYSTEM_CALLBACK_STALL_MS
  ) return "audio-callback-stalled";
  if (snapshot.lastSignalAtMs === null) return null;
  const delay = SYSTEM_SILENCE_RECOVERY_DELAYS_MS[
    Math.min(snapshot.recoveryAttempt, SYSTEM_SILENCE_RECOVERY_DELAYS_MS.length - 1)
  ] ?? SYSTEM_SILENCE_RECOVERY_DELAYS_MS.at(-1)!;
  const signalSilentForMs = snapshot.nowMs - snapshot.lastSignalAtMs;
  const timeSinceRecoveryMs = snapshot.lastRecoveryAtMs === null
    ? Number.POSITIVE_INFINITY
    : snapshot.nowMs - snapshot.lastRecoveryAtMs;
  return signalSilentForMs >= delay && timeSinceRecoveryMs >= delay ? "system-signal-stalled" : null;
};

const withTimeout = async <T,>(promise: Promise<T>, timeoutMs: number): Promise<T> => {
  let timeoutId: number | undefined;
  try {
    return await Promise.race([
      promise,
      new Promise<T>((_resolve, reject) => {
        timeoutId = window.setTimeout(() => reject(new Error("media-open-timeout")), timeoutMs);
      }),
    ]);
  } finally {
    if (timeoutId !== undefined) window.clearTimeout(timeoutId);
  }
};

export const publisherFailureDiagnostic = (sourceKind: AudioSourceKind, error: unknown) => {
  const fallback = sourceLabel(sourceKind);
  const message = describeMediaError(error);
  if (error instanceof Error) {
    if (error.message.startsWith("publisher_create_failed_")) {
      return {
        displayMessage: `${fallback}还没成功接入后端发布链路，请检查本地后端服务和当前面试是否已开始。`,
        state: "error" as const,
        stage: "failed" as const,
        errorCode: "publisher-create-failed" as const,
      };
    }
    if (error.message === "publisher_websocket_failed") {
      return {
        displayMessage: `${fallback}已采集，但实时传输通道建立失败，请检查后端 WebSocket 是否可用。`,
        state: "reconnecting" as const,
        stage: "failed" as const,
        errorCode: "publisher-websocket-failed" as const,
      };
    }
    if (error.message.startsWith("system-audio-unavailable")) {
      return {
        displayMessage: "电脑输出没有拿到系统播放音频；请先让面试官声音在这台电脑上实际播放。",
        state: "unavailable" as const,
        stage: "unsupported" as const,
        errorCode: "adapter-required" as const,
      };
    }
  }
  if (error instanceof DOMException && error.name === "NotAllowedError") {
    return {
      displayMessage: `${fallback}权限被系统拒绝，请在系统设置中授权后重试。`,
      state: "permission-denied" as const,
      stage: "permission-denied" as const,
      errorCode: "permission-denied" as const,
    };
  }
  return {
    displayMessage: `${fallback}启动失败：${message}`,
    state: "unavailable" as const,
    stage: sourceKind === "system" ? "unsupported" as const : "failed" as const,
    errorCode: sourceKind === "system" ? "adapter-required" as const : "source-unavailable" as const,
  };
};

export const publisherFailureIsTerminal = (error: unknown) =>
  error instanceof Error && /publisher_create_failed_[^_]+_(401|403|404|409|410)$/.test(error.message);

const connectProcessor = (context: AudioContext, processor: AudioNode) => {
  const sink = context.createGain();
  sink.gain.value = 0;
  processor.connect(sink);
  sink.connect(context.destination);
  return sink;
};

interface AudioCaptureProcessor {
  readonly processor: AudioNode;
  readonly sink: GainNode;
  readonly mode: "audio-worklet" | "script-processor";
  readonly detach: () => void;
}

const createAudioCaptureProcessor = async (
  context: AudioContext,
  onSamples: (samples: Float32Array, timing: CaptureBatchTiming) => void,
): Promise<AudioCaptureProcessor> => {
  if (context.audioWorklet && typeof AudioWorkletNode !== "undefined") {
    try {
      await context.audioWorklet.addModule(new URL("./pcm-capture.worklet.js", import.meta.url));
      const processor = new AudioWorkletNode(context, "offersteady-pcm-capture", {
        numberOfInputs: 1,
        numberOfOutputs: 1,
        outputChannelCount: [1],
      });
      let previousCallbackCount = 0;
      let previousPostMessageCount = 0;
      let previousAllocationCount = 1;
      processor.port.onmessage = event => {
        const rendererReceiveAtMs = Date.now();
        const payload = event.data as {
          readonly samples?: unknown;
          readonly audioWorkletOutputAtMs?: unknown;
          readonly callbackCount?: unknown;
          readonly postMessageCount?: unknown;
          readonly allocationCount?: unknown;
        };
        const samples = payload?.samples;
        const callbackCount = typeof payload.callbackCount === "number" ? payload.callbackCount : previousCallbackCount + 1;
        const postMessageCount = typeof payload.postMessageCount === "number" ? payload.postMessageCount : previousPostMessageCount + 1;
        const allocationCount = typeof payload.allocationCount === "number" ? payload.allocationCount : previousAllocationCount + 1;
        if (samples instanceof Float32Array) onSamples(samples, {
          audioWorkletOutputAtMs: typeof payload.audioWorkletOutputAtMs === "number"
            ? payload.audioWorkletOutputAtMs
            : rendererReceiveAtMs,
          rendererReceiveAtMs,
          workletCallbackCount: Math.max(0, callbackCount - previousCallbackCount),
          workletPostMessageCount: Math.max(0, postMessageCount - previousPostMessageCount),
          float32ArrayAllocations: Math.max(0, allocationCount - previousAllocationCount),
        });
        previousCallbackCount = callbackCount;
        previousPostMessageCount = postMessageCount;
        previousAllocationCount = allocationCount;
      };
      const sink = connectProcessor(context, processor);
      return {
        processor,
        sink,
        mode: "audio-worklet",
        detach: () => { processor.port.onmessage = null; },
      };
    } catch {
      // Older Electron builds and restrictive worklet loaders keep the tested
      // ScriptProcessor fallback so capture still works instead of failing.
    }
  }
  const processor = context.createScriptProcessor(1024, 1, 1);
  processor.onaudioprocess = event => {
    const receivedAtMs = Date.now();
    onSamples(event.inputBuffer.getChannelData(0), {
      audioWorkletOutputAtMs: receivedAtMs,
      rendererReceiveAtMs: receivedAtMs,
      workletCallbackCount: 1,
      workletPostMessageCount: 1,
      float32ArrayAllocations: 0,
    });
  };
  const sink = connectProcessor(context, processor);
  return {
    processor,
    sink,
    mode: "script-processor",
    detach: () => { processor.onaudioprocess = null; },
  };
};

const sourceLabel = (sourceKind: AudioSourceKind) => sourceKind === "microphone" ? "麦克风" : "电脑输出";

const concatBytes = (chunks: readonly Uint8Array[]): Uint8Array => {
  const total = chunks.reduce((sum, chunk) => sum + chunk.byteLength, 0);
  const combined = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    combined.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return combined;
};

const bytesToBase64 = (payload: Uint8Array): string => {
  let binary = "";
  const batchSize = 0x8000;
  for (let index = 0; index < payload.length; index += batchSize) {
    const slice = payload.subarray(index, index + batchSize);
    binary += String.fromCharCode(...slice);
  }
  return btoa(binary);
};

const toWebSocketEndpoint = (apiBaseUrl: string, path: string) => {
  const url = new URL(apiBaseUrl);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = `${url.pathname.replace(/\/$/, "")}${path}`;
  return url.toString();
};

const downsampleToPcm16 = (input: Float32Array, inputSampleRate: number, targetSampleRate = 16_000): Uint8Array => {
  if (input.length === 0) return new Uint8Array();
  const ratio = inputSampleRate / targetSampleRate;
  const outputLength = Math.max(1, Math.round(input.length / ratio));
  const pcm = new Uint8Array(outputLength * 2);
  let outputOffset = 0;
  for (let index = 0; index < outputLength; index += 1) {
    const start = Math.floor(index * ratio);
    const end = Math.min(input.length, Math.floor((index + 1) * ratio));
    let sum = 0;
    let count = 0;
    for (let sampleIndex = start; sampleIndex < end; sampleIndex += 1) {
      sum += input[sampleIndex] ?? 0;
      count += 1;
    }
    const averaged = count > 0 ? sum / count : input[start] ?? 0;
    const normalized = Math.max(-1, Math.min(1, averaged));
    const value = normalized < 0 ? normalized * 0x8000 : normalized * 0x7fff;
    const clamped = Math.max(-32768, Math.min(32767, Math.round(value)));
    pcm[outputOffset] = clamped & 0xff;
    pcm[outputOffset + 1] = (clamped >> 8) & 0xff;
    outputOffset += 2;
  }
  return pcm;
};

export class SpeechSegmenter {
  private lifecycle: SpeechTurnLifecycle = "idle";
  private segmentId: string | null = null;
  private startedAtMs = 0;
  private lastSpeechAtMs = 0;
  private lastInterimAtMs = 0;
  private revision = 0;
  private readonly unsentChunks: Uint8Array[] = [];
  private readonly preSpeechChunks: Uint8Array[] = [];
  private emitted = false;
  private attackStartedAtMs = -1;
  private vadTriggeredAtMs = 0;
  private speechConfirmedAtMs = 0;
  private noiseFloor: number;
  private turnPeakRms = 0;
  private sourceGeneration = 0;
  private readonly config: SpeechEndpointingConfig;

  constructor(private readonly sourceKind: AudioSourceKind, config: Partial<SpeechEndpointingConfig> = {}) {
    this.noiseFloor = sourceKind === "system" ? 0.0001 : 0.00035;
    this.config = { ...commercialSpeechEndpointingDefaults, ...config };
  }

  get currentNoiseFloor(): number {
    return this.noiseFloor;
  }

  get currentState(): SpeechTurnLifecycle {
    return this.lifecycle;
  }

  get currentGeneration(): number {
    return this.sourceGeneration;
  }

  get currentThresholds(): { readonly start: number; readonly continuation: number } {
    return this.thresholds();
  }

  private thresholds(): { readonly start: number; readonly continuation: number } {
    if (this.config.mode === "legacy-threshold") {
      return this.sourceKind === "system"
        ? { start: SYSTEM_SPEECH_START_THRESHOLD, continuation: SYSTEM_SPEECH_CONTINUE_THRESHOLD }
        : { start: MICROPHONE_SPEECH_START_THRESHOLD, continuation: MICROPHONE_SPEECH_CONTINUE_THRESHOLD };
    }
    const profile = this.vadProfile();
    return {
      start: Math.min(profile.startCeiling, Math.max(profile.startFloor, this.noiseFloor * profile.startNoiseMultiplier)),
      continuation: Math.min(profile.continuationCeiling, Math.max(profile.continuationFloor, this.noiseFloor * profile.continuationNoiseMultiplier)),
    };
  }

  private vadProfile(): SourceVadProfile {
    return this.sourceKind === "system" ? SYSTEM_VAD_PROFILE : MICROPHONE_VAD_PROFILE;
  }

  private observeNoise(rms: number): void {
    const ceiling = this.sourceKind === "system" ? 0.0025 : 0.008;
    if (!Number.isFinite(rms) || rms < 0 || rms >= ceiling) return;
    const next = this.noiseFloor * 0.94 + rms * 0.06;
    const minimum = this.sourceKind === "system" ? 0.00005 : 0.0001;
    const maximum = this.sourceKind === "system" ? 0.0015 : 0.004;
    this.noiseFloor = Math.max(minimum, Math.min(maximum, next));
  }

  push(payload: Uint8Array, nowMs: number, rms: number): SegmentSnapshot[] {
    const { start: startThreshold, continuation: continueThreshold } = this.thresholds();
    if (this.lifecycle === "idle") {
      if (payload.byteLength > 0) {
        this.preSpeechChunks.push(payload);
        while (this.preSpeechChunks.length > PRE_SPEECH_BUFFER_LIMIT) this.preSpeechChunks.shift();
      }
      if (rms < startThreshold) {
        this.observeNoise(rms);
        this.attackStartedAtMs = -1;
        return [];
      }
      const attackMs = this.config.mode === "legacy-threshold" ? 0 : this.vadProfile().attackMs;
      if (this.attackStartedAtMs < 0) {
        this.attackStartedAtMs = nowMs;
        this.vadTriggeredAtMs = nowMs;
      }
      if (nowMs - this.attackStartedAtMs < attackMs) return [];
      this.segmentId = `${this.sourceKind}-${nowMs}-${Math.random().toString(36).slice(2, 8)}`;
      this.sourceGeneration += 1;
      this.lifecycle = "speaking";
      this.startedAtMs = this.attackStartedAtMs;
      this.speechConfirmedAtMs = nowMs;
      this.lastSpeechAtMs = nowMs;
      this.turnPeakRms = rms;
      this.lastInterimAtMs = nowMs;
      this.emitted = false;
      if (this.preSpeechChunks.length > 0) this.unsentChunks.push(...this.preSpeechChunks);
      this.preSpeechChunks.length = 0;
      if (nowMs - this.startedAtMs >= this.vadProfile().minimumSpeechMs) {
        this.lastInterimAtMs = nowMs;
        this.emitted = true;
        return [this.snapshot(nowMs, false)];
      }
      return [];
    }

    this.turnPeakRms = Math.max(this.turnPeakRms, rms);
    const peakReleaseThreshold = this.sourceKind === "microphone" && this.config.mode === "commercial-adaptive"
      ? Math.min(this.vadProfile().startCeiling, this.turnPeakRms * MICROPHONE_TURN_PEAK_RELEASE_RATIO)
      : 0;
    const resumeThreshold = this.lifecycle === "tail"
      ? Math.max(startThreshold, peakReleaseThreshold)
      : Math.max(continueThreshold, peakReleaseThreshold);
    const speaking = rms >= resumeThreshold;
    if (payload.byteLength > 0) this.unsentChunks.push(payload);
    const maximumTurnMs = this.config.mode === "legacy-threshold" ? MAX_SEGMENT_DURATION_MS : this.config.maximumTurnMs;
    if (nowMs - this.startedAtMs >= maximumTurnMs) {
      const boundedFinalSnapshot = this.finalize(nowMs, "max-duration");
      this.reset();
      return [boundedFinalSnapshot];
    }
    if (speaking) {
      this.lifecycle = "speaking";
      this.lastSpeechAtMs = nowMs;
      if ((!this.emitted && nowMs - this.startedAtMs >= this.config.minimumSpeechMs) || nowMs - this.lastInterimAtMs >= this.config.interimIntervalMs) {
        this.lastInterimAtMs = nowMs;
        this.emitted = true;
        return [this.snapshot(nowMs, false)];
      }
      return [];
    }

    this.lifecycle = "tail";
    this.observeNoise(rms);
    const silenceFinalizeMs = this.config.mode === "legacy-threshold"
      ? (this.sourceKind === "system" ? this.config.systemTailMs : this.config.microphoneTailMs)
      : this.vadProfile().silenceMs;
    if (nowMs - this.lastSpeechAtMs < silenceFinalizeMs) return [];
    if (!this.emitted && this.lastSpeechAtMs - this.startedAtMs < this.config.minimumSpeechMs) {
      this.reset();
      return [];
    }
    const finalSnapshot = this.finalize(nowMs, "silence");
    this.reset();
    return [finalSnapshot];
  }

  flush(nowMs: number, reason: RealtimeFinalizationReason = "capture-stop"): SegmentSnapshot[] {
    if (!this.segmentId) return [];
    const finalSnapshot = this.finalize(nowMs, reason);
    this.reset();
    return [finalSnapshot];
  }

  private finalize(nowMs: number, reason: RealtimeFinalizationReason): SegmentSnapshot {
    this.lifecycle = "committing";
    return this.snapshot(nowMs, true, reason);
  }

  private snapshot(nowMs: number, isFinal: boolean, finalizationReason?: RealtimeFinalizationReason): SegmentSnapshot {
    this.revision += 1;
    const payload = concatBytes(this.unsentChunks);
    this.unsentChunks.length = 0;
    return {
      sequence: this.revision - 1,
      segmentId: this.segmentId ?? `${this.sourceKind}-${nowMs}`,
      revision: this.revision,
      capturedAtMs: nowMs,
      startedAtMs: this.startedAtMs,
      vadTriggeredAtMs: this.vadTriggeredAtMs || this.startedAtMs,
      speechConfirmedAtMs: this.speechConfirmedAtMs || this.startedAtMs,
      endedAtMs: nowMs,
      durationMs: Math.max(20, nowMs - this.startedAtMs),
      isFinal,
      turnState: isFinal ? "committing" : this.lifecycle === "tail" ? "tail" : "speaking",
      ...(finalizationReason ? { finalizationReason } : {}),
      sourceGeneration: this.sourceGeneration,
      ...(isFinal ? { terminalId: `${this.segmentId ?? this.sourceKind}:${this.sourceGeneration}:${this.revision}` } : {}),
      payload,
    };
  }

  private reset() {
    this.segmentId = null;
    this.lifecycle = "idle";
    this.startedAtMs = 0;
    this.lastSpeechAtMs = 0;
    this.lastInterimAtMs = 0;
    this.revision = 0;
    this.unsentChunks.length = 0;
    this.preSpeechChunks.length = 0;
    this.emitted = false;
    this.attackStartedAtMs = -1;
    this.vadTriggeredAtMs = 0;
    this.speechConfirmedAtMs = 0;
    this.turnPeakRms = 0;
  }
}

export class DesktopRealtimePublisher {
  private readonly fetchImpl: typeof fetch;
  private readonly sequencer = new SourceFrameSequencer();
  private readonly microphoneAdapter = new MicrophoneAudioAdapter();
  private readonly systemAudioAdapter = new SystemAudioAdapter();
  private runtimes: RuntimeHandle[] = [];
  private latestHealth = new Map<AudioSourceKind, HealthSnapshot>();
  private frameCounts = new Map<AudioSourceKind, number>();
  private readonly sendBuffers = new Map<AudioSourceKind, BoundedAudioFrameBuffer>();
  private readonly lastFailureNotice = new Map<AudioSourceKind, { message: string; atMs: number }>();
  private readonly sourceRecoveryInFlight = new Map<AudioSourceKind, Promise<boolean>>();
  private readonly microphoneSwitch: SerializedLatestSourceSwitch;
  private captureStarted = false;
  private lastSystemSignalAtMs: number | null = null;
  private lastSystemRecoveryAtMs: number | null = null;
  private systemRecoveryAttempt = 0;
  private stopped = false;
  private transport: MultiplexedRealtimeTransport | null = null;
  private transportRecovery: Promise<void> | null = null;
  private readonly healthUpdates: HealthUpdateScheduler<readonly AudioSourceHealth[]>;
  private readonly reliability = new RealtimeReliabilityController();
  private readonly resourceCounters = new CaptureResourceCounters();
  private readonly transportDiagnostics: RealtimeTransportDiagnostics;
  private readonly sourceInputs = new Map<AudioSourceKind, SourceStartInput>();
  private watchdogTimer: number | null = null;
  private transportWatchdogRecoveryInFlight = false;
  private transportSequenceResetInProgress = false;
  private readonly transportRecoveryAck = new FreshTransportAckGate<MultiplexedRealtimeTransport>({
    setTimeout: (handler, timeoutMs) => window.setTimeout(handler, timeoutMs),
    clearTimeout: timer => window.clearTimeout(timer),
  });
  private readonly replacementPublisherBudget = new ReplacementPublisherBudget(MAX_REPLACEMENT_PUBLISHER_ATTEMPTS);

  constructor(private readonly options: RealtimePublisherOptions) {
    this.fetchImpl = options.fetchImpl ?? ((input, init) => window.fetch(input, init));
    this.transportDiagnostics = new RealtimeTransportDiagnostics(options.binding.sessionId, (snapshot) => {
      console.info("[realtime-audio-transport-diagnostics]", snapshot);
      window.offersteady.publishRealtimeTransportDiagnostics?.(snapshot as unknown as Record<string, unknown>);
    });
    this.healthUpdates = new HealthUpdateScheduler((health) => this.options.onHealth(health), 100);
    this.sendBuffers.set("microphone", new BoundedAudioFrameBuffer(MAX_PENDING_AUDIO_BYTES));
    this.sendBuffers.set("system", new BoundedAudioFrameBuffer(MAX_PENDING_AUDIO_BYTES));
    this.microphoneSwitch = new SerializedLatestSourceSwitch(options.microphoneId);
  }

  async start() {
    this.stopped = false;
    this.transportDiagnostics.start();
    this.options.onCaptureState("reconnecting");
    try {
      await this.openTransport();
    } catch (error) {
      this.transport?.stop();
      this.transport = null;
      const diagnostic = publisherFailureDiagnostic("microphone", error);
      this.options.onCaptureState("error");
      this.options.onFailure(`实时音频连接失败，请重新连接助手后再开始面试：${diagnostic.displayMessage}`);
      throw error;
    }
    // Electron is the single media owner for the unsigned beta. Start the
    // microphone first so a pending display-media permission cannot block the
    // candidate channel, then open the system loopback on the same app identity.
    const enabledChannels = new Set<AudioSourceKind>(this.options.diagnosticAudioChannels ?? ["microphone", "system"]);
    for (const sourceKind of enabledChannels) this.reliability.start(sourceKind);
    const initialMicrophoneId = this.microphoneSwitch.desired;
    const microphoneRuntime = enabledChannels.has("microphone") ? await this.startSource({
      sourceKind: "microphone",
      sourceId: initialMicrophoneId,
      open: () => this.microphoneAdapter.open(initialMicrophoneId),
    }) : null;
    if (microphoneRuntime) this.microphoneSwitch.markApplied(initialMicrophoneId);
    const systemRuntime = enabledChannels.has("system") ? await this.startSource({
      sourceKind: "system",
      sourceId: this.options.systemAudioId || "system-loopback",
      open: () => this.systemAudioAdapter.open(),
    }) : null;
    const runtimes = [microphoneRuntime, systemRuntime];
    this.runtimes.push(...runtimes.filter((runtime): runtime is WebAudioSourceRuntime => runtime !== null));
    this.captureStarted = true;
    if (microphoneRuntime && this.microphoneSwitch.desired !== initialMicrophoneId) {
      void this.switchMicrophone(this.microphoneSwitch.desired);
    }
    if (this.runtimes.length > 0) {
      this.startWatchdog();
      this.options.onServerEvent?.({
        kind: "connection-state",
        payload: { captureOwner: desktopCaptureArchitecture, transport: "websocket-v2" },
      });
      this.options.onCaptureState("capturing");
      return;
    }
    this.options.onCaptureState("error");
    this.options.onFailure("麦克风和电脑输出都没有成功启动，请检查系统授权和设备选择。");
    throw new Error("all_audio_sources_failed");
  }

  async stop() {
    this.stopped = true;
    this.captureStarted = false;
    this.transportDiagnostics.publish();
    this.transportDiagnostics.stop();
    this.transport?.stop();
    this.transport = null;
    this.transportRecoveryAck.cancel("publisher-stopped");
    this.transportRecovery = null;
    if (this.watchdogTimer !== null) {
      window.clearInterval(this.watchdogTimer);
      this.resourceCounters.removeTimer();
    }
    this.watchdogTimer = null;
    await Promise.all(this.runtimes.map(runtime => runtime.stop()));
    this.runtimes = [];
    this.latestHealth.clear();
    this.lastFailureNotice.clear();
    this.sourceRecoveryInFlight.clear();
    this.lastSystemSignalAtMs = null;
    this.lastSystemRecoveryAtMs = null;
    this.systemRecoveryAttempt = 0;
    this.sendBuffers.forEach((buffer) => buffer.clear());
    this.sourceInputs.clear();
    this.healthUpdates.dispose();
    this.options.onHealth([]);
  }

  async switchMicrophone(sourceId: string): Promise<void> {
    this.microphoneSwitch.stage(sourceId);
    if (!this.captureStarted || this.stopped) return;
    await this.microphoneSwitch.request(sourceId, async target => {
      const input: SourceStartInput = {
        sourceKind: "microphone",
        sourceId: target,
        open: () => this.microphoneAdapter.open(target),
      };
      let recovered = await this.recoverSource(input, "device-change");
      if (!this.stopped && this.sourceInputs.get("microphone")?.sourceId !== target) {
        recovered = await this.recoverSource(input, "device-change");
      }
      return recovered && this.sourceInputs.get("microphone")?.sourceId === target;
    });
  }

  private async startSource(input: SourceStartInput): Promise<WebAudioSourceRuntime | null> {
    let media: OpenAudioSource | null = null;
    let pendingContext: AudioContext | null = null;
    let pendingNode: MediaStreamAudioSourceNode | null = null;
    let pendingCaptureProcessor: AudioCaptureProcessor | null = null;
    let trackedAudioContext = false;
    let trackedAudioNodes = 0;
    let trackedMediaTracks = 0;
    let trackedCaptureListener = false;
    try {
      this.sourceInputs.set(input.sourceKind, input);
      this.updateHealth({
        sourceId: input.sourceId,
        sourceKind: input.sourceKind,
        label: sourceLabel(input.sourceKind),
        state: "reconnecting",
        level: 0,
        active: false,
      });
      media = await withTimeout(input.open(), MEDIA_OPEN_TIMEOUT_MS);
      const openedMedia = media;
      this.updateHealth({
        sourceId: openedMedia.descriptor.id || input.sourceId,
        sourceKind: input.sourceKind,
        label: openedMedia.descriptor.label || sourceLabel(input.sourceKind),
        state: "silent",
        stage: "track-live",
        level: 0,
        active: true,
      });
      const context = new AudioContext();
      pendingContext = context;
      this.resourceCounters.addAudioContext();
      trackedAudioContext = true;
      await context.resume().catch(() => undefined);
      const node = context.createMediaStreamSource(openedMedia.stream);
      pendingNode = node;
      this.resourceCounters.addAudioNodes(4);
      trackedAudioNodes = 4;
      this.resourceCounters.addMediaTracks(openedMedia.stream.getTracks().length);
      trackedMediaTracks = openedMedia.stream.getTracks().length;
      const segmenter = new SpeechSegmenter(input.sourceKind, { mode: this.options.endpointingMode ?? "commercial-adaptive" });
      const openedAtMs = Date.now();
      let lastProcessAtMs = openedAtMs;
      let closing = false;

      const processSamples = (channel: Float32Array, captureTiming: CaptureBatchTiming) => {
        if (this.stopped) return;
        this.transportDiagnostics.recordCaptureFrame(input.sourceKind);
        this.transportDiagnostics.recordPublisherInputFrame(input.sourceKind);
        const rms = calculateRms(channel);
        const nowMs = Date.now();
        lastProcessAtMs = nowMs;
        this.reliability.recordAudioCapture(input.sourceKind, nowMs);
        this.resourceCounters.recordWorkletBatch(input.sourceKind, {
          callbackCount: captureTiming.workletCallbackCount,
          postMessageCount: captureTiming.workletPostMessageCount,
          audioBytes: channel.byteLength,
          float32ArrayAllocations: captureTiming.float32ArrayAllocations,
        });
        if (input.sourceKind === "system" && rms >= SYSTEM_SPEECH_CONTINUE_THRESHOLD) {
          this.lastSystemSignalAtMs = nowMs;
          this.lastSystemRecoveryAtMs = null;
          this.systemRecoveryAttempt = 0;
        }
        this.updateHealth({
          sourceId: openedMedia.descriptor.id || input.sourceId,
          sourceKind: input.sourceKind,
          label: openedMedia.descriptor.label,
          state: rms >= (input.sourceKind === "system" ? SYSTEM_SPEECH_CONTINUE_THRESHOLD : MICROPHONE_SPEECH_CONTINUE_THRESHOLD) ? "receiving" : "silent",
          stage: rms >= (input.sourceKind === "system" ? SYSTEM_SPEECH_CONTINUE_THRESHOLD : MICROPHONE_SPEECH_CONTINUE_THRESHOLD) ? "signal-detected" : "track-live",
          level: Number(rms.toFixed(3)),
          noiseFloor: Number(segmenter.currentNoiseFloor.toFixed(5)),
          endpointingMode: this.options.endpointingMode ?? "commercial-adaptive",
          turnState: segmenter.currentState,
          sourceGeneration: segmenter.currentGeneration,
          ...(rms >= (input.sourceKind === "system" ? SYSTEM_SPEECH_CONTINUE_THRESHOLD : MICROPHONE_SPEECH_CONTINUE_THRESHOLD) ? { lastSignalAtMs: nowMs } : {}),
          active: true,
        });
        const pcm16 = downsampleToPcm16(channel, context.sampleRate);
        const pcmConversionCompleteAtMs = Date.now();
        const frames = segmenter.push(pcm16, nowMs, rms);
        for (const snapshot of frames) {
          if (snapshot.payload.byteLength === 0) continue;
          const frame = createAudioFrame(this.sequencer, {
            sessionId: this.options.binding.sessionId,
            deviceId: this.options.binding.deviceId,
            sourceId: openedMedia.descriptor.id || input.sourceId,
            sourceKind: input.sourceKind,
            capturedAtMs: snapshot.capturedAtMs,
            durationMs: snapshot.durationMs,
            payload: snapshot.payload,
          });
          const eventPayload = {
            type: "audio-frame",
            deviceId: frame.deviceId,
            sourceId: frame.sourceId,
            sourceKind: frame.sourceKind,
            sequence: frame.sequence,
            segmentId: snapshot.segmentId,
            revision: snapshot.revision,
            capturedAtMs: frame.capturedAtMs,
            startedAtMs: snapshot.startedAtMs,
            vadTriggeredAtMs: snapshot.vadTriggeredAtMs,
            speechConfirmedAtMs: snapshot.speechConfirmedAtMs,
            endedAtMs: snapshot.endedAtMs,
            durationMs: frame.durationMs,
            codec: "pcm-s16le",
            sampleRateHz: 16_000,
            channels: 1,
            isFinal: snapshot.isFinal,
            turnState: snapshot.turnState,
            finalizationReason: snapshot.finalizationReason,
            sourceGeneration: snapshot.sourceGeneration,
            terminalId: snapshot.terminalId,
            traceId: `${input.sourceKind}:${snapshot.segmentId}:${snapshot.revision}:${frame.sequence}`,
            diagnostics: {
              desktopVadConfirmAtMs: snapshot.speechConfirmedAtMs,
              desktopAudioWorkletOutputAtMs: captureTiming.audioWorkletOutputAtMs,
              desktopRendererReceiveAtMs: captureTiming.rendererReceiveAtMs,
              desktopPcmConversionAtMs: pcmConversionCompleteAtMs,
              audioRms: Number(rms.toFixed(6)),
              audioPeak: Number(Math.max(...channel.map(sample => Math.abs(sample))).toFixed(6)),
              noiseFloor: Number(segmenter.currentNoiseFloor.toFixed(6)),
              vadThreshold: Number(segmenter.currentThresholds.start.toFixed(6)),
              vadState: segmenter.currentState,
              payloadDurationMs: Math.round(snapshot.payload.byteLength / 32),
              frameSeq: frame.sequence,
            },
            audioBase64: bytesToBase64(snapshot.payload),
          };
          const frameCount = (this.frameCounts.get(input.sourceKind) ?? 0) + 1;
          this.frameCounts.set(input.sourceKind, frameCount);
          this.reliability.recordFrameProduced(input.sourceKind, nowMs);
          this.updateHealth({
            sourceId: openedMedia.descriptor.id || input.sourceId,
            sourceKind: input.sourceKind,
            label: openedMedia.descriptor.label,
            state: "receiving",
            stage: "frames-produced",
            level: Number(rms.toFixed(3)),
            lastSignalAtMs: nowMs,
            frameCount,
            lastFrameAtMs: nowMs,
            active: true,
          });
          this.sendFrame(input.sourceKind, eventPayload, frame, openedMedia.descriptor.id || input.sourceId);
        }
      };
      const captureProcessor = await createAudioCaptureProcessor(context, processSamples);
      pendingCaptureProcessor = captureProcessor;
      this.transportDiagnostics.recordAudioListenerAttached(input.sourceKind);
      trackedCaptureListener = true;
      const { processor, sink } = captureProcessor;
      node.connect(processor);
      this.updateHealth({
        ...(this.latestHealth.get(input.sourceKind) ?? {
          sourceId: openedMedia.descriptor.id || input.sourceId,
          sourceKind: input.sourceKind,
          label: openedMedia.descriptor.label,
          state: "silent" as const,
          level: 0,
          active: true,
        }),
        captureProcessor: captureProcessor.mode,
      });

      const audioTrack = openedMedia.stream.getAudioTracks()[0];
      const recoveryTimer = input.sourceKind === "system" && audioTrack
        ? window.setInterval(() => {
          if (closing || this.stopped || this.sourceRecoveryInFlight.has(input.sourceKind)) return;
          const reason = systemAudioRecoveryReason({
            nowMs: Date.now(),
            openedAtMs,
            lastProcessAtMs,
            lastSignalAtMs: this.lastSystemSignalAtMs,
            lastRecoveryAtMs: this.lastSystemRecoveryAtMs,
            recoveryAttempt: this.systemRecoveryAttempt,
            trackReadyState: audioTrack.readyState,
            trackMuted: audioTrack.muted,
            contextState: context.state,
          });
          if (reason) void this.recoverSource(input, reason);
        }, SYSTEM_RECOVERY_CHECK_MS)
        : null;
      if (recoveryTimer !== null) this.resourceCounters.addTimer();

      const handleTrackEnded = () => {
        if (closing || this.stopped) return;
        this.updateHealth({
          sourceId: openedMedia.descriptor.id || input.sourceId,
          sourceKind: input.sourceKind,
          label: openedMedia.descriptor.label,
          state: "unavailable",
          stage: "failed",
          level: 0,
          active: false,
          errorCode: "source-unavailable",
        });
        void this.recoverSource(input, "track-ended");
      };
      const tracks = openedMedia.stream.getTracks();
      tracks.forEach((track) => track.addEventListener("ended", handleTrackEnded));
      this.resourceCounters.addListeners(tracks.length + 1);

      const stop = async () => {
        closing = true;
        if (recoveryTimer !== null) {
          window.clearInterval(recoveryTimer);
          this.resourceCounters.removeTimer();
        }
        tracks.forEach((track) => track.removeEventListener("ended", handleTrackEnded));
        this.resourceCounters.removeListeners(tracks.length + 1);
        const tailFrames = segmenter.flush(Date.now());
        for (const snapshot of tailFrames) {
          if (snapshot.payload.byteLength === 0) continue;
          const frame = createAudioFrame(this.sequencer, {
            sessionId: this.options.binding.sessionId,
            deviceId: this.options.binding.deviceId,
            sourceId: openedMedia.descriptor.id || input.sourceId,
            sourceKind: input.sourceKind,
            capturedAtMs: snapshot.capturedAtMs,
            durationMs: snapshot.durationMs,
            payload: snapshot.payload,
          });
          this.sendFrame(input.sourceKind, {
            type: "audio-frame",
            deviceId: frame.deviceId,
            sourceId: frame.sourceId,
            sourceKind: frame.sourceKind,
            sequence: frame.sequence,
            segmentId: snapshot.segmentId,
            revision: snapshot.revision,
            capturedAtMs: frame.capturedAtMs,
            startedAtMs: snapshot.startedAtMs,
            vadTriggeredAtMs: snapshot.vadTriggeredAtMs,
            speechConfirmedAtMs: snapshot.speechConfirmedAtMs,
            endedAtMs: snapshot.endedAtMs,
            durationMs: frame.durationMs,
            codec: "pcm-s16le",
            sampleRateHz: 16_000,
            channels: 1,
            isFinal: true,
            turnState: snapshot.turnState,
            finalizationReason: snapshot.finalizationReason,
            sourceGeneration: snapshot.sourceGeneration,
            terminalId: snapshot.terminalId,
            traceId: `${input.sourceKind}:${snapshot.segmentId}:${snapshot.revision}:${frame.sequence}`,
            audioBase64: bytesToBase64(snapshot.payload),
          }, frame, openedMedia.descriptor.id || input.sourceId);
        }
        captureProcessor.detach();
        this.transportDiagnostics.recordAudioListenerDetached(input.sourceKind);
        trackedCaptureListener = false;
        processor.disconnect();
        sink.disconnect();
        node.disconnect();
        openedMedia.close();
        await context.close().catch(() => undefined);
        this.resourceCounters.removeMediaTracks(tracks.length);
        this.resourceCounters.removeAudioNodes(4);
        this.resourceCounters.removeAudioContext();
        this.reliability.remove(input.sourceKind);
      };

      return {
        sourceId: openedMedia.descriptor.id || input.sourceId,
        sourceKind: input.sourceKind,
        label: openedMedia.descriptor.label,
        media: openedMedia,
        context,
        processor,
        sink,
        node,
        stop,
      };
    } catch (error) {
      pendingCaptureProcessor?.detach();
      if (trackedCaptureListener) this.transportDiagnostics.recordAudioListenerDetached(input.sourceKind);
      pendingCaptureProcessor?.processor.disconnect();
      pendingCaptureProcessor?.sink.disconnect();
      pendingNode?.disconnect();
      media?.close();
      if (pendingContext) await pendingContext.close().catch(() => undefined);
      if (trackedMediaTracks > 0) this.resourceCounters.removeMediaTracks(trackedMediaTracks);
      if (trackedAudioNodes > 0) this.resourceCounters.removeAudioNodes(trackedAudioNodes);
      if (trackedAudioContext) this.resourceCounters.removeAudioContext();
      const diagnostic = publisherFailureDiagnostic(input.sourceKind, error);
      this.updateHealth({
        sourceId: input.sourceId,
        sourceKind: input.sourceKind,
        label: sourceLabel(input.sourceKind),
        state: diagnostic.state,
        stage: diagnostic.stage,
        level: 0,
        active: false,
        errorCode: diagnostic.errorCode,
      });
      this.options.onFailure(diagnostic.displayMessage);
      return null;
    }
  }

  private recoverSource(input: SourceStartInput, reason: AudioSourceRecoveryReason): Promise<boolean> {
    if (this.stopped || this.transportSequenceResetInProgress) return Promise.resolve(false);
    const existing = this.sourceRecoveryInFlight.get(input.sourceKind);
    if (existing) return existing;
    const recovery = (async () => {
      this.reliability.markRecovering(input.sourceKind, reason);
      this.emitReliability();
      if (input.sourceKind === "system") {
        this.lastSystemRecoveryAtMs = Date.now();
        this.systemRecoveryAttempt += 1;
      }
      const current = this.runtimes.find(
        (runtime): runtime is WebAudioSourceRuntime => "sourceKind" in runtime && runtime.sourceKind === input.sourceKind,
      );
      this.updateHealth({
        sourceId: current?.sourceId || input.sourceId,
        sourceKind: input.sourceKind,
        label: current?.label || sourceLabel(input.sourceKind),
        state: "reconnecting",
        stage: "track-live",
        level: 0,
        active: true,
        errorCode: "audio-gap",
      });
      this.options.onServerEvent?.({
        kind: "degraded",
        payload: {
          reason: input.sourceKind === "system" ? "system-audio-auto-recovery" : "microphone-device-change",
          recoveryReason: reason,
          sourceKind: input.sourceKind,
          attempt: input.sourceKind === "system" ? this.systemRecoveryAttempt : 1,
        },
      });
      if (current) {
        await current.stop();
        this.runtimes = this.runtimes.filter(runtime => runtime !== current);
      }
      if (this.stopped) return false;
      this.reliability.start(input.sourceKind);
      this.reliability.markRecovering(input.sourceKind, reason);
      const recovered = await this.startSource(input);
      if (recovered) {
        this.runtimes.push(recovered);
        this.options.onServerEvent?.({
          kind: "connection-state",
          payload: { sourceKind: input.sourceKind, state: "reconnected", recoveryReason: reason },
        });
        return true;
      }
      this.options.onFailure(`${sourceLabel(input.sourceKind)}自动恢复失败，请在助手中重新开始面试。`);
      return false;
    })();
    const tracked = recovery.finally(() => {
      if (this.sourceRecoveryInFlight.get(input.sourceKind) === tracked) {
        this.sourceRecoveryInFlight.delete(input.sourceKind);
      }
    });
    this.sourceRecoveryInFlight.set(input.sourceKind, tracked);
    return tracked;
  }

  private async createPublisher(sourceKind: AudioSourceKind | "mixed"): Promise<PublisherTokenResponse> {
    const response = await this.fetchImpl(`${this.options.apiBaseUrl}/realtime-speech/publishers`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        userId: this.options.binding.ownerUserId,
        sessionId: this.options.binding.sessionId,
        sourceKind,
        clientName: `${this.options.binding.displayName} · ${sourceKind}`,
        deviceId: this.options.binding.deviceId,
        manualCode: this.options.binding.manualCode,
      }),
    });
    if (!response.ok) throw new Error(`publisher_create_failed_${sourceKind}_${response.status}`);
    const payload = await response.json() as { data: PublisherTokenResponse };
    return payload.data;
  }

  private async openTransport(pending: readonly Record<string, unknown>[] = []): Promise<MultiplexedRealtimeTransport> {
    const transportPublisher = await this.createPublisher("mixed");
    let transport: MultiplexedRealtimeTransport;
    transport = new MultiplexedRealtimeTransport({
      apiBaseUrl: this.options.apiBaseUrl,
      token: transportPublisher.token,
      onEvent: event => {
        if (this.transport === transport) this.handleTransportEvent(event, transport);
      },
      onState: state => {
        if (this.transport !== transport) return;
        const recovering = this.transportSequenceResetInProgress || this.transportRecoveryAck.isWaitingFor(transport);
        this.options.onCaptureState(state === "connected" && !recovering ? "capturing" : "reconnecting");
      },
      onTerminal: input => {
        if (this.transport !== transport || this.stopped) return;
        this.transportRecoveryAck.fail(transport, input.reason);
        void this.recoverTransport(input);
      },
      diagnostics: this.transportDiagnostics,
    });
    this.transport = transport;
    await transport.start();
    const resumeOffsets = await transport.waitForResumeOffsets();
    this.sequencer.alignNext("microphone", resumeOffsets.microphone + 1);
    this.sequencer.alignNext("system", resumeOffsets.system + 1);
    for (const payload of pending) transport.enqueue(payload);
    return transport;
  }

  private recoverTransport(input: { readonly code: number; readonly reason: string; readonly pending: readonly Record<string, unknown>[]; readonly resetSequence?: boolean }): Promise<void> {
    if (this.transportRecovery) return this.transportRecovery;
    const failedTransport = this.transport;
    this.transportRecovery = (async () => {
      const sourceInputs = [...this.sourceInputs.values()];
      this.transportSequenceResetInProgress = true;
      this.options.onCaptureState("reconnecting");
      this.options.onServerEvent?.({ kind: "degraded", payload: {
        reason: input.reason,
        message: "实时音频顺序已失配，正在自动重建发布链路并从新序列继续。",
        closeCode: input.code,
        pendingFrames: input.pending.length,
      } });
      failedTransport?.stop();
      if (this.transport === failedTransport) this.transport = null;
      await Promise.all(this.runtimes.map(runtime => runtime.stop()));
      this.runtimes = [];
      this.sequencer.reset();
      this.sendBuffers.forEach(buffer => buffer.clear());
      let lastError: unknown = null;
      let attempt = 0;
      while (!this.stopped && this.replacementPublisherBudget.claimAttempt()) {
        attempt += 1;
        try {
          if (attempt > 1) await new Promise<void>(resolve => window.setTimeout(resolve, 250 * attempt));
          const replacementTransport = await this.openTransport();
          const acknowledged = this.transportRecoveryAck.wait(replacementTransport, REPLACEMENT_PUBLISHER_ACK_TIMEOUT_MS);
          void acknowledged.catch(() => undefined);
          this.transportSequenceResetInProgress = false;
          for (const sourceInput of sourceInputs) {
            this.reliability.start(sourceInput.sourceKind);
            this.reliability.markRecovering(sourceInput.sourceKind, "transport-sequence-reset");
            const recovered = await this.startSource(sourceInput);
            if (recovered) this.runtimes.push(recovered);
          }
          await acknowledged;
          this.options.onServerEvent?.({ kind: "connection-state", payload: {
            state: "transport-reset",
            recoveryReason: input.reason,
            attempt,
            discardedStaleFrames: input.pending.length,
          } });
          return;
        } catch (error) {
          lastError = error;
          this.transportSequenceResetInProgress = true;
          const failedAttempt = this.transport;
          if (failedAttempt) this.transportRecoveryAck.fail(failedAttempt, "replacement-publisher-attempt-failed");
          failedAttempt?.stop();
          if (this.transport === failedAttempt) this.transport = null;
          await Promise.all(this.runtimes.map(runtime => runtime.stop()));
          this.runtimes = [];
          this.sequencer.reset();
          this.sendBuffers.forEach(buffer => buffer.clear());
        }
      }
      if (!this.stopped) {
        for (const sourceInput of sourceInputs) {
          this.reliability.markTerminalLost(sourceInput.sourceKind, "publisher-recovery-exhausted");
          const existing = this.latestHealth.get(sourceInput.sourceKind);
          this.updateHealth({
            ...(existing ?? {
              sourceId: sourceInput.sourceId,
              sourceKind: sourceInput.sourceKind,
              label: sourceLabel(sourceInput.sourceKind),
            }),
            state: "error",
            stage: "failed",
            level: 0,
            active: false,
            pendingFrameCount: 0,
            oldestPendingFrameAgeMs: 0,
            errorCode: "publisher-recovery-exhausted",
          });
        }
        this.transportSequenceResetInProgress = false;
        const diagnostic = publisherFailureDiagnostic("microphone", lastError);
        this.options.onFailure(`实时音频上传已停止，请退出当前面试并重新连接助手：${diagnostic.displayMessage}`);
        this.options.onCaptureState("error");
        this.options.onServerEvent?.({ kind: "degraded", payload: {
          reason: "publisher-recovery-exhausted",
          message: "实时音频上传已停止，需要显式重新连接。",
          retryable: false,
        } });
        this.emitReliability();
      }
    })().finally(() => {
      this.transportSequenceResetInProgress = false;
      this.transportRecovery = null;
    });
    return this.transportRecovery;
  }

  private handleTransportEvent(event: { readonly kind?: string; readonly payload?: Record<string, unknown> }, transport: MultiplexedRealtimeTransport): void {
    const payload = event.payload ?? {};
    const sourceKind = payload?.sourceKind;
    if (sourceKind === "microphone" || sourceKind === "system") {
      const existing = this.latestHealth.get(sourceKind);
      if (typeof payload.lastFrameSentAtMs === "number") {
        this.reliability.recordFrameSent(sourceKind, payload.lastFrameSentAtMs, typeof payload.pendingFrames === "number" ? payload.pendingFrames : undefined);
      }
      if (typeof payload.pendingFrames === "number") this.reliability.updatePendingFrames(sourceKind, payload.pendingFrames);
      if (event.kind === "frame-accepted" || event.kind === "terminal-accepted") {
        this.reliability.recordFrameAck(sourceKind, typeof payload.lastAckAtMs === "number" ? payload.lastAckAtMs : Date.now(), typeof payload.pendingFrames === "number" ? payload.pendingFrames : 0);
        const recovered = this.transportRecoveryAck.acknowledge(transport);
        if (recovered) this.options.onCaptureState("capturing");
        this.replacementPublisherBudget.recordAcknowledgement(transport.pendingPayloads().length > 0);
      }
      if (typeof payload.qwenAppendAtMs === "number") this.reliability.recordQwenAppend(sourceKind, payload.qwenAppendAtMs);
      if (existing && (event.kind === "frame-accepted" || event.kind === "terminal-accepted") && typeof payload.sequence === "number") {
        this.sendBuffers.get(sourceKind)?.acknowledge(String(payload.sourceId ?? existing.sourceId), payload.sequence);
        this.transportDiagnostics.setRingBufferDepth(sourceKind, this.sendBuffers.get(sourceKind)?.depth() ?? 0);
      }
      if (existing && (event.kind === "delivery-diagnostics" || event.kind === "sequence-gap" || event.kind === "frame-accepted" || event.kind === "terminal-accepted")) {
        this.updateHealth({
          ...existing,
          ...(typeof payload.pendingFrames === "number" ? { pendingFrameCount: payload.pendingFrames } : {}),
          ...(typeof payload.oldestPendingFrameAgeMs === "number" ? { oldestPendingFrameAgeMs: payload.oldestPendingFrameAgeMs } : {}),
          ...(typeof payload.droppedFrames === "number" ? { droppedFrameCount: payload.droppedFrames } : {}),
          ...(typeof payload.reconnectCount === "number" ? { reconnectCount: payload.reconnectCount } : {}),
          ...(typeof payload.lastAckAtMs === "number" ? { lastAckAtMs: payload.lastAckAtMs } : event.kind === "frame-accepted" ? { lastAckAtMs: Date.now() } : {}),
          ...(typeof payload.terminalPendingSinceMs === "number" ? { terminalPendingSinceMs: payload.terminalPendingSinceMs } : {}),
          ...(typeof payload.terminalAgeMs === "number" ? { terminalAgeMs: payload.terminalAgeMs } : {}),
          ...(typeof payload.terminalResendCount === "number" ? { terminalResendCount: payload.terminalResendCount } : {}),
          ...(typeof payload.terminalAckAtMs === "number" ? { terminalAckAtMs: payload.terminalAckAtMs } : event.kind === "terminal-accepted" ? { terminalAckAtMs: Date.now() } : {}),
          ...(typeof payload.reason === "string" ? { lastReconnectReason: payload.reason } : {}),
        });
      }
    }
    this.options.onServerEvent?.(event);
    this.emitReliability();
  }

  private sendFrame(
    sourceKind: AudioSourceKind,
    payload: Record<string, unknown>,
    frame: ReturnType<typeof createAudioFrame>,
    sourceId: string,
  ) {
    if (this.transportSequenceResetInProgress) return;
    const ringBufferWriteAtMs = Date.now();
    const diagnostics = typeof payload.diagnostics === "object" && payload.diagnostics !== null
      ? payload.diagnostics as Record<string, unknown>
      : {};
    const queuedPayload = {
      ...payload,
      diagnostics: {
        ...diagnostics,
        desktopRingBufferWriteAtMs: ringBufferWriteAtMs,
        desktopPublisherEnqueueAtMs: Date.now(),
      },
    };
    if (this.transport) {
      this.sendBuffers.get(sourceKind)?.push(frame);
      this.transportDiagnostics.setRingBufferDepth(sourceKind, this.sendBuffers.get(sourceKind)?.depth() ?? 0);
      this.transport.enqueue(queuedPayload);
      this.transportRecoveryAck.markMediaPending(this.transport);
      this.reliability.recordFrameSent(sourceKind, Date.now());
      this.refreshOwnedBufferBytes();
      return;
    }
    this.sendBuffers.get(sourceKind)?.clear();
    this.reliability.markTerminalLost(sourceKind, "publisher-transport-missing");
    this.updateHealth({
      sourceId,
      sourceKind,
      label: sourceLabel(sourceKind),
      state: "error",
      stage: "failed",
      level: 0,
      active: false,
      frameCount: this.frameCounts.get(sourceKind) ?? 0,
      lastFrameAtMs: Date.now(),
      pendingFrameCount: 0,
      errorCode: "publisher-transport-missing",
    });
    this.options.onCaptureState("error");
    this._notifyFailure(sourceKind, `${sourceLabel(sourceKind)}上传连接已停止，请退出当前面试并重新连接助手。`);
    this.emitReliability();
  }


  reliabilitySnapshot(): DesktopRealtimeReliabilitySnapshot {
    this.refreshOwnedBufferBytes();
    return {
      capturedAtMs: Date.now(),
      sessionId: this.options.binding.sessionId,
      sources: this.reliability.snapshot(),
      resources: this.resourceCounters.snapshot(),
    };
  }

  private emitReliability(): void {
    this.options.onReliability?.(this.reliabilitySnapshot());
  }

  private refreshOwnedBufferBytes(): void {
    const bufferedPcmBytes = [...this.sendBuffers.values()].reduce((sum, buffer) => sum + buffer.pendingByteLength(), 0);
    this.resourceCounters.setOwnedArrayBufferBytes(bufferedPcmBytes);
  }

  private startWatchdog(): void {
    if (this.watchdogTimer !== null) window.clearInterval(this.watchdogTimer);
    this.resourceCounters.addTimer();
    this.watchdogTimer = window.setInterval(() => {
      if (this.stopped) return;
      const decisions = this.reliability.evaluate();
      this.emitReliability();
      for (const decision of decisions) {
        if (decision.action === "recover-source") {
          const input = this.sourceInputs.get(decision.sourceKind);
          if (input) void this.recoverSource(input, "watchdog-capture-lost");
        } else if (decision.action === "recover-transport" && !this.transportWatchdogRecoveryInFlight) {
          this.transportWatchdogRecoveryInFlight = true;
          const pending = this.transport?.pendingPayloads() ?? [];
          void this.recoverTransport({ code: 0, reason: "watchdog-frame-ack-stalled", pending })
            .finally(() => { this.transportWatchdogRecoveryInFlight = false; });
        }
      }
    }, 1_000);
  }

  private _notifyFailure(sourceKind: AudioSourceKind, message: string) {
    const nowMs = Date.now();
    const last = this.lastFailureNotice.get(sourceKind);
    if (!last || last.message !== message || nowMs - last.atMs > 1500) {
      this.lastFailureNotice.set(sourceKind, { message, atMs: nowMs });
      this.options.onFailure(message);
    }
  }


  private parseSocketEvent(raw: unknown): PublisherSocketEvent | null {
    if (typeof raw !== "string") return null;
    try {
      return JSON.parse(raw) as PublisherSocketEvent;
    } catch {
      return null;
    }
  }

  private updateHealth(next: HealthSnapshot) {
    const merged = {
      ...this.latestHealth.get(next.sourceKind),
      ...next,
    };
    this.latestHealth.set(next.sourceKind, merged);
    const ordered = [...this.latestHealth.values()]
      .sort((left, right) => left.sourceKind.localeCompare(right.sourceKind))
      .map(({ active, ...health }) => health);
    this.healthUpdates.push(ordered);
  }
}
