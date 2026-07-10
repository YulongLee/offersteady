import type { AudioSourceHealth, AudioSourceKind } from "@offersteady/protocol";

import { MicrophoneAudioAdapter, SystemAudioAdapter, describeMediaError, type OpenAudioSource } from "./audio-source-adapter";
import { calculateRms } from "./signal-diagnostics";

interface LocalSourceMonitorOptions {
  readonly microphoneId: string;
  readonly systemAudioId: string;
  readonly onHealth: (health: readonly AudioSourceHealth[]) => void;
  readonly onFailure?: (message: string) => void;
}

interface SourceRuntime {
  readonly sourceKind: AudioSourceKind;
  readonly media: OpenAudioSource;
  readonly context: AudioContext;
  readonly node: MediaStreamAudioSourceNode;
  readonly processor: ScriptProcessorNode;
  readonly stop: () => Promise<void>;
}

const SIGNAL_THRESHOLD = 0.0008;
const MEDIA_OPEN_TIMEOUT_MS = 6500;

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

const connectProcessor = (context: AudioContext, processor: ScriptProcessorNode) => {
  const sink = context.createGain();
  sink.gain.value = 0;
  processor.connect(sink);
  sink.connect(context.destination);
  return sink;
};

const errorStateFor = (error: unknown): AudioSourceHealth["state"] => {
  if (error instanceof DOMException && error.name === "NotAllowedError") return "permission-denied";
  return "unavailable";
};

const errorCodeFor = (error: unknown): AudioSourceHealth["errorCode"] => {
  if (error instanceof DOMException && error.name === "NotAllowedError") return "permission-denied";
  return "source-unavailable";
};

export class LocalSourceMonitor {
  private readonly microphoneAdapter = new MicrophoneAudioAdapter();
  private readonly systemAudioAdapter = new SystemAudioAdapter();
  private readonly latestHealth = new Map<AudioSourceKind, AudioSourceHealth>();
  private runtimes: SourceRuntime[] = [];
  private stopped = false;

  constructor(private readonly options: LocalSourceMonitorOptions) {}

  async start() {
    this.stopped = false;
    const microphoneRuntime = await this.startSource({
      sourceKind: "microphone",
      sourceId: this.options.microphoneId,
      fallbackLabel: "麦克风",
      open: () => this.microphoneAdapter.open(this.options.microphoneId),
    });
    const systemRuntime = await this.startSource({
      sourceKind: "system",
      sourceId: this.options.systemAudioId,
      fallbackLabel: "电脑输出",
      open: () => this.systemAudioAdapter.open(),
    });
    this.runtimes = [microphoneRuntime, systemRuntime].filter((runtime): runtime is SourceRuntime => runtime !== null);
  }

  async stop() {
    this.stopped = true;
    await Promise.all(this.runtimes.map((runtime) => runtime.stop()));
    this.runtimes = [];
    this.latestHealth.clear();
    this.options.onHealth([]);
  }

  private async startSource(input: {
    readonly sourceKind: AudioSourceKind;
    readonly sourceId: string;
    readonly fallbackLabel: string;
    readonly open: () => Promise<OpenAudioSource>;
  }): Promise<SourceRuntime | null> {
    try {
      this.updateHealth({
        sourceId: input.sourceId,
        sourceKind: input.sourceKind,
        label: input.fallbackLabel,
        state: "permission-required",
        stage: "permission-required",
        level: 0,
      });
      const media = await withTimeout(input.open(), MEDIA_OPEN_TIMEOUT_MS);
      const context = new AudioContext();
      await context.resume().catch(() => undefined);
      const node = context.createMediaStreamSource(media.stream);
      const processor = context.createScriptProcessor(4096, 1, 1);
      const sink = connectProcessor(context, processor);

      node.connect(processor);
      this.updateHealth({
        sourceId: media.descriptor.id || input.sourceId,
        sourceKind: input.sourceKind,
        label: media.descriptor.label || input.fallbackLabel,
        state: "silent",
        stage: "track-live",
        level: 0,
      });

      processor.onaudioprocess = (event) => {
        if (this.stopped) return;
        const samples = event.inputBuffer.getChannelData(0);
        const rms = calculateRms(samples);
        const nowMs = Date.now();
        this.updateHealth({
          sourceId: media.descriptor.id || input.sourceId,
          sourceKind: input.sourceKind,
          label: media.descriptor.label || input.fallbackLabel,
          state: rms >= SIGNAL_THRESHOLD ? "receiving" : "silent",
          stage: rms >= SIGNAL_THRESHOLD ? "signal-detected" : "track-live",
          level: Number(rms.toFixed(3)),
          ...(rms >= SIGNAL_THRESHOLD ? { lastSignalAtMs: nowMs } : {}),
        });
      };

      media.stream.getTracks().forEach((track) => {
        track.addEventListener("ended", () => {
          this.updateHealth({
            sourceId: media.descriptor.id || input.sourceId,
            sourceKind: input.sourceKind,
            label: media.descriptor.label || input.fallbackLabel,
            state: "unavailable",
            stage: "failed",
            level: 0,
            errorCode: "source-unavailable",
          });
        });
      });

      return {
        sourceKind: input.sourceKind,
        media,
        context,
        node,
        processor,
        stop: async () => {
          processor.disconnect();
          sink.disconnect();
          node.disconnect();
          media.close();
          await context.close().catch(() => undefined);
        },
      };
    } catch (error) {
      const message = describeMediaError(error);
      const nextErrorCode = errorCodeFor(error);
      this.updateHealth({
        sourceId: input.sourceId,
        sourceKind: input.sourceKind,
        label: input.fallbackLabel,
        state: errorStateFor(error),
        stage: nextErrorCode === "permission-denied" ? "permission-denied" : input.sourceKind === "system" ? "unsupported" : "failed",
        level: 0,
        ...(nextErrorCode ? { errorCode: nextErrorCode } : {}),
      });
      this.options.onFailure?.(`${input.fallbackLabel}检测失败：${message}`);
      return null;
    }
  }

  private updateHealth(health: AudioSourceHealth) {
    this.latestHealth.set(health.sourceKind, health);
    this.options.onHealth(
      [...this.latestHealth.values()].sort((left, right) => left.sourceKind.localeCompare(right.sourceKind)),
    );
  }
}
