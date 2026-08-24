import type { AudioSourceHealth, AudioSourceKind, RealtimeFinalizationReason, RealtimeTurnState } from "@offersteady/protocol";

import { BoundedAudioFrameBuffer, createAudioFrame, SourceFrameSequencer } from "./audio-frame-buffer";
import { MicrophoneAudioAdapter, SystemAudioAdapter, describeMediaError, type OpenAudioSource } from "./audio-source-adapter";
import { calculateRms } from "./signal-diagnostics";
import { MultiplexedRealtimeTransport } from "./multiplexed-realtime-transport";

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
}

interface RealtimePublisherOptions extends RealtimePublisherCallbacks {
  readonly apiBaseUrl: string;
  readonly binding: DesktopBinding;
  readonly microphoneId: string;
  readonly systemAudioId: string;
  readonly endpointingMode?: EndpointingMode;
  readonly fetchImpl?: typeof fetch;
}

export const sessionCapturePermissionPolicy = {
  requestPermissionOnSessionStart: false,
  systemAudioCapture: "electron-display-loopback",
  captureOwner: "electron-single-owner",
} as const;

export const desktopCaptureArchitecture = "electron-single-owner" as const;

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
const MICROPHONE_SILENCE_FINALIZE_MS = 700;
const SYSTEM_SILENCE_FINALIZE_MS = 500;
const MAX_SEGMENT_DURATION_MS = 30_000;
const MIN_EMIT_SPEECH_MS = 60;
const PRE_SPEECH_BUFFER_LIMIT = 4;

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
const MAX_PENDING_UPLOAD_FRAMES = 64;
const HTTP_PUBLISH_THROTTLE_MS = 12;
const HTTP_PUBLISH_RETRY_DELAY_MS = 120;
const HTTP_PUBLISH_RETRY_LIMIT = 10;
const MEDIA_OPEN_TIMEOUT_MS = 6500;
const SYSTEM_RECOVERY_CHECK_MS = 2_000;
const SYSTEM_CALLBACK_STALL_MS = 4_000;
const SYSTEM_RECOVERY_STARTUP_GRACE_MS = 6_000;
const SYSTEM_SILENCE_RECOVERY_DELAYS_MS = [30_000, 120_000, 300_000] as const;

export type SystemAudioRecoveryReason =
  | "track-ended"
  | "track-muted"
  | "audio-context-not-running"
  | "audio-callback-stalled"
  | "system-signal-stalled";

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

interface QueuedUploadFrame {
  readonly sourceId: string;
  readonly sourceKind: AudioSourceKind;
  readonly payload: Record<string, unknown>;
  readonly frame: ReturnType<typeof createAudioFrame>;
}

interface UploadQueueState {
  readonly items: QueuedUploadFrame[];
  uploading: boolean;
  terminalFailure: boolean;
  consecutiveFailures: number;
}

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
  onSamples: (samples: Float32Array) => void,
): Promise<AudioCaptureProcessor> => {
  if (context.audioWorklet && typeof AudioWorkletNode !== "undefined") {
    try {
      await context.audioWorklet.addModule(new URL("./pcm-capture.worklet.js", import.meta.url));
      const processor = new AudioWorkletNode(context, "offersteady-pcm-capture", {
        numberOfInputs: 1,
        numberOfOutputs: 1,
        outputChannelCount: [1],
      });
      processor.port.onmessage = event => {
        const samples = event.data;
        if (samples instanceof Float32Array) onSamples(samples);
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
  processor.onaudioprocess = event => onSamples(event.inputBuffer.getChannelData(0));
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

const allowFrameRetryByError = (errorCode: string): boolean => errorCode !== "permission-denied" && errorCode !== "adapter-required";

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

    const resumeThreshold = this.lifecycle === "tail" ? startThreshold : continueThreshold;
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
  private readonly uploadQueues = new Map<AudioSourceKind, UploadQueueState>();
  private readonly lastFailureNotice = new Map<AudioSourceKind, { message: string; atMs: number }>();
  private readonly sourceRecoveryInFlight = new Set<AudioSourceKind>();
  private lastSystemSignalAtMs: number | null = null;
  private lastSystemRecoveryAtMs: number | null = null;
  private systemRecoveryAttempt = 0;
  private stopped = false;
  private transport: MultiplexedRealtimeTransport | null = null;
  private transportRecovery: Promise<void> | null = null;

  constructor(private readonly options: RealtimePublisherOptions) {
    this.fetchImpl = options.fetchImpl ?? ((input, init) => window.fetch(input, init));
    this.sendBuffers.set("microphone", new BoundedAudioFrameBuffer(MAX_PENDING_AUDIO_BYTES));
    this.sendBuffers.set("system", new BoundedAudioFrameBuffer(MAX_PENDING_AUDIO_BYTES));
    this.uploadQueues.set("microphone", { items: [], uploading: false, terminalFailure: false, consecutiveFailures: 0 });
    this.uploadQueues.set("system", { items: [], uploading: false, terminalFailure: false, consecutiveFailures: 0 });
  }

  async start() {
    this.stopped = false;
    this.options.onCaptureState("reconnecting");
    try {
      await this.openTransport();
    } catch (error) {
      this.transport?.stop();
      this.transport = null;
      const diagnostic = publisherFailureDiagnostic("microphone", error);
      this.options.onServerEvent?.({
        kind: "degraded",
        payload: {
          reason: diagnostic.errorCode,
          message: "实时长连接暂不可用，已自动切换到兼容传输，收音将继续工作。",
          transport: "http-frame-ingest",
        },
      });
    }
    // Electron is the single media owner for the unsigned beta. Start the
    // microphone first so a pending display-media permission cannot block the
    // candidate channel, then open the system loopback on the same app identity.
    const microphoneRuntime = await this.startSource({
      sourceKind: "microphone",
      sourceId: this.options.microphoneId,
      open: () => this.microphoneAdapter.open(this.options.microphoneId),
    });
    const systemRuntime = await this.startSource({
      sourceKind: "system",
      sourceId: this.options.systemAudioId || "system-loopback",
      open: () => this.systemAudioAdapter.open(),
    });
    const runtimes = [microphoneRuntime, systemRuntime];
    this.runtimes.push(...runtimes.filter((runtime): runtime is WebAudioSourceRuntime => runtime !== null));
    if (this.runtimes.length > 0) {
      this.options.onServerEvent?.({
        kind: "connection-state",
        payload: { captureOwner: desktopCaptureArchitecture, transport: this.transport ? "websocket-v2" : "http-frame-ingest" },
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
    this.transport?.stop();
    this.transport = null;
    this.transportRecovery = null;
    await Promise.all(this.runtimes.map(runtime => runtime.stop()));
    this.runtimes = [];
    this.latestHealth.clear();
    this.uploadQueues.forEach((queueState) => {
      queueState.items.length = 0;
      queueState.uploading = false;
      queueState.terminalFailure = false;
      queueState.consecutiveFailures = 0;
    });
    this.lastFailureNotice.clear();
    this.sourceRecoveryInFlight.clear();
    this.lastSystemSignalAtMs = null;
    this.lastSystemRecoveryAtMs = null;
    this.systemRecoveryAttempt = 0;
    this.sendBuffers.forEach((buffer) => buffer.clear());
    this.options.onHealth([]);
  }

  private async startSource(input: SourceStartInput): Promise<WebAudioSourceRuntime | null> {
    let media: OpenAudioSource | null = null;
    try {
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
      await context.resume().catch(() => undefined);
      const node = context.createMediaStreamSource(openedMedia.stream);
      const segmenter = new SpeechSegmenter(input.sourceKind, { mode: this.options.endpointingMode ?? "commercial-adaptive" });
      const openedAtMs = Date.now();
      let lastProcessAtMs = openedAtMs;
      let closing = false;

      const processSamples = (channel: Float32Array) => {
        if (this.stopped) return;
        const rms = calculateRms(channel);
        const nowMs = Date.now();
        lastProcessAtMs = nowMs;
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
            audioBase64: bytesToBase64(snapshot.payload),
          };
          const frameCount = (this.frameCounts.get(input.sourceKind) ?? 0) + 1;
          this.frameCounts.set(input.sourceKind, frameCount);
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
          this.sendFrameHttp(input.sourceKind, eventPayload, frame, openedMedia.descriptor.id || input.sourceId);
        }
      };
      const captureProcessor = await createAudioCaptureProcessor(context, processSamples);
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

      const stop = async () => {
        closing = true;
        if (recoveryTimer !== null) window.clearInterval(recoveryTimer);
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
          this.sendFrameHttp(input.sourceKind, {
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
        processor.disconnect();
        sink.disconnect();
        node.disconnect();
        openedMedia.close();
        await context.close().catch(() => undefined);
      };

      openedMedia.stream.getTracks().forEach((track) => {
        track.addEventListener("ended", () => {
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
          if (input.sourceKind === "system") void this.recoverSource(input, "track-ended");
        });
      });

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
      media?.close();
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

  private async recoverSource(input: SourceStartInput, reason: SystemAudioRecoveryReason) {
    if (this.stopped || this.sourceRecoveryInFlight.has(input.sourceKind)) return;
    this.sourceRecoveryInFlight.add(input.sourceKind);
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
        reason: "system-audio-auto-recovery",
        recoveryReason: reason,
        sourceKind: input.sourceKind,
        attempt: this.systemRecoveryAttempt,
      },
    });
    try {
      if (current) {
        await current.stop();
        this.runtimes = this.runtimes.filter(runtime => runtime !== current);
      }
      if (this.stopped) return;
      const recovered = await this.startSource(input);
      if (recovered) {
        this.runtimes.push(recovered);
        this.options.onServerEvent?.({
          kind: "connection-state",
          payload: { sourceKind: input.sourceKind, state: "reconnected", recoveryReason: reason },
        });
      } else {
        this.options.onFailure(`${sourceLabel(input.sourceKind)}自动恢复失败，请在助手中重新开始面试。`);
      }
    } finally {
      this.sourceRecoveryInFlight.delete(input.sourceKind);
    }
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

  private async openTransport(pending: readonly Record<string, unknown>[] = []): Promise<void> {
    const transportPublisher = await this.createPublisher("mixed");
    let transport: MultiplexedRealtimeTransport;
    transport = new MultiplexedRealtimeTransport({
      apiBaseUrl: this.options.apiBaseUrl,
      token: transportPublisher.token,
      onEvent: event => this.handleTransportEvent(event),
      onState: state => this.options.onCaptureState(state === "failed" ? "reconnecting" : state === "connected" ? "capturing" : "reconnecting"),
      onTerminal: input => {
        if (this.transport !== transport || this.stopped) return;
        void this.recoverTransport(input);
      },
    });
    this.transport = transport;
    await transport.start();
    for (const payload of pending) transport.enqueue(payload);
  }

  private recoverTransport(input: { readonly code: number; readonly reason: string; readonly pending: readonly Record<string, unknown>[] }): Promise<void> {
    if (this.transportRecovery) return this.transportRecovery;
    const failedTransport = this.transport;
    this.transportRecovery = (async () => {
      this.options.onCaptureState("reconnecting");
      this.options.onServerEvent?.({ kind: "degraded", payload: {
        reason: input.reason,
        message: "实时发布凭据已失效，正在自动连接当前面试并恢复未确认音频。",
        closeCode: input.code,
        pendingFrames: input.pending.length,
      } });
      failedTransport?.stop();
      if (this.transport === failedTransport) this.transport = null;
      let lastError: unknown = null;
      for (let attempt = 1; attempt <= 3 && !this.stopped; attempt += 1) {
        try {
          if (attempt > 1) await new Promise<void>(resolve => window.setTimeout(resolve, 250 * attempt));
          await this.openTransport(input.pending);
          this.options.onServerEvent?.({ kind: "connection-state", payload: {
            state: "credential-refreshed",
            recoveryReason: input.reason,
            attempt,
            restoredFrames: input.pending.length,
          } });
          return;
        } catch (error) {
          lastError = error;
          this.transport?.stop();
          this.transport = null;
        }
      }
      if (!this.stopped) {
        const diagnostic = publisherFailureDiagnostic("microphone", lastError);
        this.options.onFailure(`实时发布通道自动恢复失败：${diagnostic.displayMessage}`);
        this.options.onCaptureState("error");
      }
    })().finally(() => {
      this.transportRecovery = null;
    });
    return this.transportRecovery;
  }

  private handleTransportEvent(event: { readonly kind?: string; readonly payload?: Record<string, unknown> }): void {
    const payload = event.payload ?? {};
    const sourceKind = payload?.sourceKind;
    if (sourceKind === "microphone" || sourceKind === "system") {
      const existing = this.latestHealth.get(sourceKind);
      if (existing && (event.kind === "frame-accepted" || event.kind === "terminal-accepted") && typeof payload.sequence === "number") {
        this.sendBuffers.get(sourceKind)?.acknowledge(String(payload.sourceId ?? existing.sourceId), payload.sequence);
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
  }

  private sendFrameHttp(
    sourceKind: AudioSourceKind,
    payload: Record<string, unknown>,
    frame: ReturnType<typeof createAudioFrame>,
    sourceId: string,
  ) {
    if (this.transport) {
      this.sendBuffers.get(sourceKind)?.push(frame);
      this.transport.enqueue(payload);
      return;
    }
    const droppedFrames = this.sendBuffers.get(sourceKind)?.push(frame) ?? [];
    if (droppedFrames.length > 0) {
      this.updateHealth({
        sourceId,
        sourceKind,
        label: sourceLabel(sourceKind),
        state: "reconnecting",
        stage: "frames-produced",
        level: Number((this.latestHealth.get(sourceKind)?.level ?? 0).toFixed(3)),
        active: true,
        frameCount: this.frameCounts.get(sourceKind) ?? 0,
        lastFrameAtMs: Date.now(),
        errorCode: "audio-gap",
      });
    }
    const queueState = this.uploadQueues.get(sourceKind);
    if (!queueState) return;
    if (queueState.terminalFailure) {
      this._notifyFailure(sourceKind, `${sourceLabel(sourceKind)}未连接，已暂停语音上报，请先重连桌面端与网页。`);
      return;
    }
    const queued = {
      sourceKind,
      sourceId,
      payload,
      frame,
    };
    if (queueState.items.length >= MAX_PENDING_UPLOAD_FRAMES) {
      const firstInterim = queueState.items.findIndex(item => item.payload.isFinal !== true);
      if (firstInterim < 0 && payload.isFinal !== true) {
        this.sendBuffers.get(sourceKind)?.acknowledge(frame.sourceId, frame.sequence);
        this._notifyFailure(sourceKind, `${sourceLabel(sourceKind)}发送队列正在保障结束帧，已跳过过期中间帧`);
        return;
      }
      const dropped = firstInterim >= 0 ? queueState.items.splice(firstInterim, 1)[0] : undefined;
      if (dropped) {
        const droppedFrame = dropped.frame;
        this.sendBuffers.get(sourceKind)?.acknowledge(droppedFrame.sourceId, droppedFrame.sequence);
      }
      if (!dropped) {
        this._notifyFailure(sourceKind, `${sourceLabel(sourceKind)}结束帧队列已满，请检查网络连接`);
        return;
      }
      this._notifyFailure(sourceKind, `${sourceLabel(sourceKind)}发送队列已满，已跳过过期中间帧并保留结束帧`);
    }
    queueState.items.push(queued);
    if (!queueState.uploading) {
      void this._drainUploadQueue(sourceKind);
    }
  }

  private async _drainUploadQueue(sourceKind: AudioSourceKind): Promise<void> {
    const queueState = this.uploadQueues.get(sourceKind);
    if (!queueState || queueState.uploading) return;
    queueState.uploading = true;
    try {
      while (!this.stopped && queueState.items.length > 0 && !queueState.terminalFailure) {
        const current = queueState.items.shift();
        if (!current) break;
        const sentAtMs = Date.now();
        try {
          const response = await this.fetchImpl(`${this.options.apiBaseUrl}/realtime-speech/frames`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ...current.payload, sentAtMs }),
          });
          if (!response.ok) {
            let errorCode = "http-frame-rejected";
            let message = "实时语音采集请求被后端拒绝。";
            try {
              const payload = await response.json() as { readonly error?: { readonly errorCode?: string; readonly message?: string } };
              if (payload?.error?.errorCode) errorCode = payload.error.errorCode;
              if (payload?.error?.message) message = payload.error.message;
            } catch {
              const fallback = await response.text().catch(() => message);
              if (fallback) message = fallback;
            }
            const isBindingTransient = response.status === 409 || errorCode.startsWith("desktop-") || errorCode === "web-heartbeat-missing" || errorCode === "session-not-active";
            if (isBindingTransient) {
              queueState.consecutiveFailures += 1;
              this._notifyFailure(sourceKind, `${sourceLabel(sourceKind)}未就绪：${message}`);
              if (queueState.consecutiveFailures <= HTTP_PUBLISH_RETRY_LIMIT) {
                queueState.items.unshift(current);
                await new Promise<void>((resolve) => {
                  window.setTimeout(resolve, HTTP_PUBLISH_RETRY_DELAY_MS * Math.max(1, Math.min(HTTP_PUBLISH_RETRY_LIMIT, queueState.consecutiveFailures)));
                });
                continue;
              }
            } else if (response.status >= 400 && response.status < 500) {
              queueState.terminalFailure = true;
              queueState.items.length = 0;
              this._notifyFailure(sourceKind, `${sourceLabel(sourceKind)}采集链路被拒绝：${message.slice(0, 120)}`);
              this.updateHealth({
                sourceId: current.sourceId,
                sourceKind,
                label: sourceLabel(sourceKind),
                state: "error",
                stage: "failed",
                level: 0,
                active: false,
                errorCode: "asr-failed",
              });
              break;
            }
            throw new Error(`publisher_http_frame_failed_${response.status}: ${message}`);
          }
          this.sendBuffers.get(sourceKind)?.acknowledge(current.sourceId, current.frame.sequence);
          queueState.consecutiveFailures = 0;
          this.lastFailureNotice.delete(sourceKind);
          const isTerminal = current.payload.isFinal === true;
          this.options.onServerEvent?.({
            kind: isTerminal ? "terminal-accepted" : "frame-accepted",
            payload: {
              sourceKind,
              sourceId: current.sourceId,
              sequence: current.frame.sequence,
              ...(isTerminal && typeof current.payload.terminalId === "string" ? { terminalId: current.payload.terminalId } : {}),
              ...(isTerminal ? { terminalAckAtMs: Date.now() } : {}),
              transport: "http-frame-ingest",
            },
          });
          this.updateHealth({
            sourceId: current.sourceId,
            sourceKind,
            label: sourceLabel(sourceKind),
            state: "receiving",
            stage: "frames-published",
            level: Number((this.latestHealth.get(sourceKind)?.level ?? 0).toFixed(3)),
            active: true,
            frameCount: this.frameCounts.get(sourceKind) ?? 0,
            lastFrameAtMs: sentAtMs,
            backendFrameCount: this.frameCounts.get(sourceKind) ?? 0,
            lastBackendFrameAtMs: Date.now(),
          });
        } catch (error) {
          queueState.consecutiveFailures += 1;
          const diagnostic = publisherFailureDiagnostic(sourceKind, error);
          this._notifyFailure(sourceKind, diagnostic.displayMessage);
          this.updateHealth({
            sourceId: current.sourceId,
            sourceKind,
            label: sourceLabel(sourceKind),
            state: diagnostic.state,
            stage: diagnostic.stage,
            level: 0,
            active: false,
            errorCode: diagnostic.errorCode,
          });
          if (!this.stopped && queueState.consecutiveFailures <= 1 && allowFrameRetryByError(diagnostic.errorCode)) {
            queueState.items.unshift(current);
            await new Promise<void>((resolve) => {
              window.setTimeout(resolve, HTTP_PUBLISH_RETRY_DELAY_MS);
            });
          } else {
            queueState.terminalFailure = true;
            queueState.items.length = 0;
            break;
          }
        }
        if (queueState.items.length > 0) {
          await new Promise<void>((resolve) => {
            window.setTimeout(resolve, HTTP_PUBLISH_THROTTLE_MS);
          });
        }
      }
    } finally {
      queueState.uploading = false;
    }
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
    this.options.onHealth(ordered);
  }
}
