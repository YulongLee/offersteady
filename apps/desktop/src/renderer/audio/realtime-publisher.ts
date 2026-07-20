import type { AudioSourceHealth, AudioSourceKind } from "@offersteady/protocol";

import { BoundedAudioFrameBuffer, createAudioFrame, SourceFrameSequencer } from "./audio-frame-buffer";
import { MicrophoneAudioAdapter, SystemAudioAdapter, describeMediaError, type OpenAudioSource } from "./audio-source-adapter";
import { calculateRms } from "./signal-diagnostics";
import { MultiplexedRealtimeTransport } from "./multiplexed-realtime-transport";

interface DesktopBinding {
  readonly sessionId: string;
  readonly ownerUserId: string;
  readonly deviceId: string;
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
  readonly fetchImpl?: typeof fetch;
}

interface RuntimeHandle {
  readonly stop: () => Promise<void>;
}

interface WebAudioSourceRuntime extends RuntimeHandle {
  readonly sourceId: string;
  readonly sourceKind: AudioSourceKind;
  readonly label: string;
  readonly media: OpenAudioSource;
  readonly context: AudioContext;
  readonly processor: ScriptProcessorNode;
  readonly sink: GainNode;
  readonly node: MediaStreamAudioSourceNode;
}

interface SegmentSnapshot {
  readonly sequence: number;
  readonly segmentId: string;
  readonly revision: number;
  readonly capturedAtMs: number;
  readonly startedAtMs: number;
  readonly endedAtMs: number;
  readonly durationMs: number;
  readonly isFinal: boolean;
  readonly payload: Uint8Array;
}

const SPEECH_START_THRESHOLD = 0.003;
const SPEECH_CONTINUE_THRESHOLD = 0.0018;
const INTERIM_INTERVAL_MS = 200;
const SILENCE_FINALIZE_MS = 320;
const MIN_EMIT_SPEECH_MS = 120;
const PRE_SPEECH_BUFFER_LIMIT = 4;
const MAX_PENDING_AUDIO_BYTES = 64_000;
const MAX_PENDING_UPLOAD_FRAMES = 64;
const HTTP_PUBLISH_THROTTLE_MS = 12;
const HTTP_PUBLISH_RETRY_DELAY_MS = 120;
const HTTP_PUBLISH_RETRY_LIMIT = 10;
const MEDIA_OPEN_TIMEOUT_MS = 6500;

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

const connectProcessor = (context: AudioContext, processor: ScriptProcessorNode) => {
  const sink = context.createGain();
  sink.gain.value = 0;
  processor.connect(sink);
  sink.connect(context.destination);
  return sink;
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

const base64ToBytes = (payload: string): Uint8Array => {
  const binary = atob(payload);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
  return bytes;
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
  private segmentId: string | null = null;
  private startedAtMs = 0;
  private lastSpeechAtMs = 0;
  private lastInterimAtMs = 0;
  private revision = 0;
  private readonly unsentChunks: Uint8Array[] = [];
  private readonly preSpeechChunks: Uint8Array[] = [];
  private emitted = false;

  constructor(private readonly sourceKind: AudioSourceKind) {}

  push(payload: Uint8Array, nowMs: number, rms: number): SegmentSnapshot[] {
    if (!this.segmentId) {
      if (payload.byteLength > 0) {
        this.preSpeechChunks.push(payload);
        while (this.preSpeechChunks.length > PRE_SPEECH_BUFFER_LIMIT) this.preSpeechChunks.shift();
      }
      if (rms < SPEECH_START_THRESHOLD) return [];
      this.segmentId = `${this.sourceKind}-${nowMs}-${Math.random().toString(36).slice(2, 8)}`;
      this.startedAtMs = nowMs;
      this.lastSpeechAtMs = nowMs;
      this.lastInterimAtMs = nowMs;
      this.emitted = false;
      if (this.preSpeechChunks.length > 0) this.unsentChunks.push(...this.preSpeechChunks);
      this.preSpeechChunks.length = 0;
      return [];
    }

    const speaking = rms >= SPEECH_CONTINUE_THRESHOLD;
    if (payload.byteLength > 0) this.unsentChunks.push(payload);
    if (speaking) {
      this.lastSpeechAtMs = nowMs;
      if ((!this.emitted && nowMs - this.startedAtMs >= MIN_EMIT_SPEECH_MS) || nowMs - this.lastInterimAtMs >= INTERIM_INTERVAL_MS) {
        this.lastInterimAtMs = nowMs;
        this.emitted = true;
        return [this.snapshot(nowMs, false)];
      }
      return [];
    }

    if (nowMs - this.lastSpeechAtMs < SILENCE_FINALIZE_MS) return [];
    if (!this.emitted && this.lastSpeechAtMs - this.startedAtMs < MIN_EMIT_SPEECH_MS) {
      this.reset();
      return [];
    }
    const finalSnapshot = this.snapshot(nowMs, true);
    this.reset();
    return [finalSnapshot];
  }

  flush(nowMs: number): SegmentSnapshot[] {
    if (!this.segmentId) return [];
    const finalSnapshot = this.snapshot(nowMs, true);
    this.reset();
    return [finalSnapshot];
  }

  private snapshot(nowMs: number, isFinal: boolean): SegmentSnapshot {
    this.revision += 1;
    const payload = concatBytes(this.unsentChunks);
    this.unsentChunks.length = 0;
    return {
      sequence: this.revision - 1,
      segmentId: this.segmentId ?? `${this.sourceKind}-${nowMs}`,
      revision: this.revision,
      capturedAtMs: nowMs,
      startedAtMs: this.startedAtMs,
      endedAtMs: nowMs,
      durationMs: Math.max(20, nowMs - this.startedAtMs),
      isFinal,
      payload,
    };
  }

  private reset() {
    this.segmentId = null;
    this.startedAtMs = 0;
    this.lastSpeechAtMs = 0;
    this.lastInterimAtMs = 0;
    this.revision = 0;
    this.unsentChunks.length = 0;
    this.preSpeechChunks.length = 0;
    this.emitted = false;
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
  private stopped = false;
  private transport: MultiplexedRealtimeTransport | null = null;

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
    const transportPublisher = await this.createPublisher("mixed");
    this.transport = new MultiplexedRealtimeTransport({
      apiBaseUrl: this.options.apiBaseUrl,
      token: transportPublisher.token,
      onEvent: event => this.options.onServerEvent?.(event),
      onState: state => this.options.onCaptureState(state === "failed" ? "error" : state === "connected" ? "capturing" : "reconnecting"),
    });
    await this.transport.start();
    const nativeAvailable = Boolean(window.offersteady?.startNativeAudioStream && window.offersteady?.onNativeAudioEvent);
    const nativeStarted = await this.startNativeCapture().catch(() => false);
    if (nativeStarted) {
      this.options.onCaptureState("capturing");
      return;
    }
    if (nativeAvailable) {
      this.options.onCaptureState("error");
      this.options.onFailure("原生双通道采集没有成功启动。为避免重复采集，正式桌面版不会自动启动第二套 WebAudio 链路。请检查系统权限后重试。");
      throw new Error("native_audio_capture_required");
    }
    const [microphoneRuntime, systemRuntime] = await Promise.all([
      this.startSource({
        sourceKind: "microphone",
        sourceId: this.options.microphoneId,
        open: () => this.microphoneAdapter.open(this.options.microphoneId),
      }),
      this.startSource({
        sourceKind: "system",
        sourceId: this.options.systemAudioId,
        open: () => this.systemAudioAdapter.open(),
      }),
    ]);
    const runtimes = [microphoneRuntime, systemRuntime];
    this.runtimes = runtimes.filter((runtime): runtime is WebAudioSourceRuntime => runtime !== null);
    if (this.runtimes.length > 0) {
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
    this.sendBuffers.forEach((buffer) => buffer.clear());
    this.options.onHealth([]);
  }

  private async startSource(input: {
    readonly sourceKind: AudioSourceKind;
    readonly sourceId: string;
    readonly open: () => Promise<OpenAudioSource>;
  }): Promise<WebAudioSourceRuntime | null> {
    let media: OpenAudioSource | null = null;
    try {
      this.updateHealth({
        sourceId: input.sourceId,
        sourceKind: input.sourceKind,
        label: sourceLabel(input.sourceKind),
        state: "permission-required",
        stage: "permission-required",
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
      const processor = context.createScriptProcessor(2048, 1, 1);
      const sink = connectProcessor(context, processor);
      const segmenter = new SpeechSegmenter(input.sourceKind);

      node.connect(processor);

      processor.onaudioprocess = (event) => {
        if (this.stopped) return;
        const channel = event.inputBuffer.getChannelData(0);
        const rms = calculateRms(channel);
        const nowMs = Date.now();
        this.updateHealth({
          sourceId: openedMedia.descriptor.id || input.sourceId,
          sourceKind: input.sourceKind,
          label: openedMedia.descriptor.label,
          state: rms >= SPEECH_CONTINUE_THRESHOLD ? "receiving" : "silent",
          stage: rms >= SPEECH_CONTINUE_THRESHOLD ? "signal-detected" : "track-live",
          level: Number(rms.toFixed(3)),
          ...(rms >= SPEECH_CONTINUE_THRESHOLD ? { lastSignalAtMs: nowMs } : {}),
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
            endedAtMs: snapshot.endedAtMs,
            durationMs: frame.durationMs,
            codec: "pcm-s16le",
            sampleRateHz: 16_000,
            channels: 1,
            isFinal: snapshot.isFinal,
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

      const stop = async () => {
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
            endedAtMs: snapshot.endedAtMs,
            durationMs: frame.durationMs,
            codec: "pcm-s16le",
            sampleRateHz: 16_000,
            channels: 1,
            isFinal: true,
            traceId: `${input.sourceKind}:${snapshot.segmentId}:${snapshot.revision}:${frame.sequence}`,
            audioBase64: bytesToBase64(snapshot.payload),
          }, frame, openedMedia.descriptor.id || input.sourceId);
        }
        processor.disconnect();
        sink.disconnect();
        node.disconnect();
        openedMedia.close();
        await context.close().catch(() => undefined);
      };

      openedMedia.stream.getTracks().forEach((track) => {
        track.addEventListener("ended", () => {
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

  private async startNativeCapture(): Promise<boolean> {
    if (!window.offersteady?.startNativeAudioStream || !window.offersteady?.onNativeAudioEvent) return false;
    const segmenters = new Map<AudioSourceKind, SpeechSegmenter>([
      ["microphone", new SpeechSegmenter("microphone")],
      ["system", new SpeechSegmenter("system")],
    ]);
    const sourceIds: Record<AudioSourceKind, string> = {
      microphone: "native-microphone",
      system: "native-system-output",
    };

    const markNativeSourcePending = (sourceKind: AudioSourceKind) => {
      const sourceId = sourceIds[sourceKind];
      this.updateHealth({
        sourceId,
        sourceKind,
        label: sourceLabel(sourceKind),
        state: "permission-required",
        stage: "permission-required",
        level: 0,
        active: false,
      });
    };

    markNativeSourcePending("microphone");
    markNativeSourcePending("system");

    const unsubscribe = window.offersteady.onNativeAudioEvent((event) => {
      if (this.stopped) return;
      if (event.sourceKind !== "microphone" && event.sourceKind !== "system") return;
      const sourceKind = event.sourceKind;
      const sourceId = event.sourceId || sourceIds[sourceKind];
      if (event.type === "status") {
        if (event.errorCode) {
          this.updateHealth({
            sourceId,
            sourceKind,
            label: sourceLabel(sourceKind),
            state: sourceKind === "system" ? "unsupported" : "error",
            stage: sourceKind === "system" ? "unsupported" : "failed",
            level: 0,
            active: false,
            errorCode: sourceKind === "system" ? "adapter-required" : "source-unavailable",
          });
          if (event.message) this.options.onFailure(event.message);
          return;
        }
        this.updateHealth({
          sourceId,
          sourceKind,
          label: sourceLabel(sourceKind),
          state: "silent",
          stage: "track-live",
          level: Number((event.level ?? 0).toFixed(3)),
          active: true,
        });
        return;
      }
      if (event.type !== "frame" || !event.audioBase64) return;
      const payloadBytes = base64ToBytes(event.audioBase64);
      if (payloadBytes.byteLength === 0) return;
      const capturedAtMs = event.capturedAtMs ?? Date.now();
      const durationMs = event.durationMs ?? 20;
      const level = Number((event.level ?? 0).toFixed(3));
      const snapshots = segmenters.get(sourceKind)?.push(payloadBytes, capturedAtMs, event.level ?? 0) ?? [];
      this.updateHealth({
        sourceId,
        sourceKind,
        label: sourceLabel(sourceKind),
        state: level >= SPEECH_CONTINUE_THRESHOLD ? "receiving" : "silent",
        stage: level >= SPEECH_CONTINUE_THRESHOLD ? "signal-detected" : "track-live",
        level,
        ...(level >= SPEECH_CONTINUE_THRESHOLD ? { lastSignalAtMs: capturedAtMs } : {}),
        active: true,
      });
      if (snapshots.length === 0) return;
      {
        if (this.stopped) return;
        for (const snapshot of snapshots) {
          if (snapshot.payload.byteLength === 0) continue;
          const frame = createAudioFrame(this.sequencer, {
            sessionId: this.options.binding.sessionId,
            deviceId: this.options.binding.deviceId,
            sourceId,
            sourceKind,
            capturedAtMs: snapshot.capturedAtMs,
            durationMs: snapshot.durationMs,
            payload: snapshot.payload,
          });
          const frameCount = (this.frameCounts.get(sourceKind) ?? 0) + 1;
          this.frameCounts.set(sourceKind, frameCount);
          this.updateHealth({
            sourceId,
            sourceKind,
            label: sourceLabel(sourceKind),
            state: "receiving",
            stage: "frames-produced",
            level,
            lastSignalAtMs: capturedAtMs,
            frameCount,
            lastFrameAtMs: capturedAtMs,
            active: true,
          });
          this.sendFrameHttp(sourceKind, {
            type: "audio-frame",
            deviceId: frame.deviceId,
            sourceId: frame.sourceId,
            sourceKind: frame.sourceKind,
            sequence: frame.sequence,
            segmentId: snapshot.segmentId,
            revision: snapshot.revision,
            capturedAtMs: frame.capturedAtMs,
            startedAtMs: snapshot.startedAtMs,
            endedAtMs: snapshot.endedAtMs,
            durationMs: snapshot.durationMs || durationMs,
            codec: "pcm-s16le",
            sampleRateHz: event.sampleRateHz ?? 16_000,
            channels: event.channels === 2 ? 2 : 1,
            isFinal: snapshot.isFinal,
            traceId: `${sourceKind}:native:${snapshot.segmentId}:${snapshot.revision}:${frame.sequence}`,
            audioBase64: bytesToBase64(snapshot.payload),
          }, frame, sourceId);
        }
      }
    });

    try {
      const result = await window.offersteady.startNativeAudioStream({
        microphoneSourceId: sourceIds.microphone,
        systemSourceId: sourceIds.system,
      });
      if (!result.ok) {
        unsubscribe();
        return false;
      }
      if (result.microphoneStarted === false) {
        this.options.onFailure("原生麦克风采集暂不可用，请检查麦克风权限和当前默认输入设备。");
      }
      if (result.systemStarted === false) {
        this.options.onFailure("原生电脑输出采集暂不可用，请检查屏幕录制权限后重试。");
      }
    } catch {
      unsubscribe();
      return false;
    }

    this.runtimes = [{
      stop: async () => {
        unsubscribe();
        await window.offersteady?.stopNativeAudioStream?.().catch(() => undefined);
        segmenters.clear();
      },
    }];
    this.options.onServerEvent?.({ kind: "connection-state", payload: { transport: "native-jsonl-websocket-v2" } });
    return true;
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
      }),
    });
    if (!response.ok) throw new Error(`publisher_create_failed_${sourceKind}`);
    const payload = await response.json() as { data: PublisherTokenResponse };
    return payload.data;
  }

  private sendFrameHttp(
    sourceKind: AudioSourceKind,
    payload: Record<string, unknown>,
    frame: ReturnType<typeof createAudioFrame>,
    sourceId: string,
  ) {
    if (this.transport) {
      const droppedFrames = this.sendBuffers.get(sourceKind)?.push(frame) ?? [];
      if (droppedFrames.length > 0) this._notifyFailure(sourceKind, `${sourceLabel(sourceKind)}网络缓冲超过 2 秒，已丢弃最旧音频并上报缺口。`);
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
    queueState.items.push({
      sourceKind,
      sourceId,
      payload,
      frame,
    });
    if (queueState.items.length > MAX_PENDING_UPLOAD_FRAMES) {
      const dropped = queueState.items.shift();
      if (dropped) {
        const droppedFrame = dropped.frame;
        this.sendBuffers.get(sourceKind)?.acknowledge(droppedFrame.sourceId, droppedFrame.sequence);
      }
      this._notifyFailure(sourceKind, `${sourceLabel(sourceKind)}发送队列已满，已丢弃旧帧`);
    }
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
          this.options.onServerEvent?.({
            kind: "frame-accepted",
            payload: {
              sourceKind,
              sourceId: current.sourceId,
              sequence: current.frame.sequence,
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
    this.latestHealth.set(next.sourceKind, next);
    const ordered = [...this.latestHealth.values()]
      .sort((left, right) => left.sourceKind.localeCompare(right.sourceKind))
      .map(({ active, ...health }) => health);
    this.options.onHealth(ordered);
  }
}
