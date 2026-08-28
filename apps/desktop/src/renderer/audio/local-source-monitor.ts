import type { AudioSourceHealth, AudioSourceKind } from "@offersteady/protocol";

import { MicrophoneAudioAdapter, SystemAudioAdapter, describeMediaError, type OpenAudioSource } from "./audio-source-adapter";
import { calculateRms } from "./signal-diagnostics";
import { WarmSourceHandoff, type AudioCalibrationSnapshot } from "./warm-source-handoff";
import { readinessFields, sourceSignalVerificationThreshold } from "./audio-readiness";

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
  readonly release: (closeMedia: boolean) => Promise<void>;
  readonly lastSignalAtMs: () => number | undefined;
  readonly calibration: () => AudioCalibrationSnapshot;
}

const MEDIA_OPEN_TIMEOUT_MS = 6500;
const CALLBACK_STALL_MS = 4_000;

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
    await Promise.all(this.runtimes.map((runtime) => runtime.release(true)));
    this.runtimes = [];
    this.latestHealth.clear();
    this.options.onHealth([]);
  }

  takeWarmSources(): WarmSourceHandoff {
    this.stopped = true;
    const runtimes = this.runtimes;
    this.runtimes = [];
    const handoff = new WarmSourceHandoff(runtimes.map(runtime => ({
      sourceKind: runtime.sourceKind,
      source: runtime.media,
      lastSignalAtMs: runtime.lastSignalAtMs(),
      calibration: runtime.calibration(),
    })));
    for (const runtime of runtimes) void runtime.release(false);
    this.latestHealth.clear();
    this.options.onHealth([]);
    return handoff;
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
      const signalThreshold = sourceSignalVerificationThreshold(input.sourceKind);
      let lastSignalAtMs: number | undefined;
      let lastCallbackAtMs = Date.now();
      let noiseFloor = input.sourceKind === "system" ? 0.0001 : 0.00035;
      let calibrationSampleCount = 0;
      let consecutiveSignalCallbacks = 0;

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
        lastCallbackAtMs = nowMs;
        if (rms < signalThreshold * 1.25) {
          noiseFloor = Math.max(
            input.sourceKind === "system" ? 0.00005 : 0.0001,
            Math.min(input.sourceKind === "system" ? 0.0005 : 0.004, noiseFloor * 0.94 + rms * 0.06),
          );
          calibrationSampleCount += 1;
        }
        consecutiveSignalCallbacks = rms >= Math.max(signalThreshold, noiseFloor * 2.4)
          ? consecutiveSignalCallbacks + 1
          : 0;
        if (consecutiveSignalCallbacks >= 2) lastSignalAtMs = nowMs;
        this.updateHealth({
          sourceId: media.descriptor.id || input.sourceId,
          sourceKind: input.sourceKind,
          label: media.descriptor.label || input.fallbackLabel,
          state: rms >= signalThreshold ? "receiving" : "silent",
          stage: rms >= signalThreshold ? "signal-detected" : "track-live",
          level: Number(rms.toFixed(3)),
          noiseFloor: Number(noiseFloor.toFixed(6)),
          ...readinessFields(lastSignalAtMs, nowMs),
        });
      };

      const stallTimer = window.setInterval(() => {
        if (this.stopped || Date.now() - lastCallbackAtMs <= CALLBACK_STALL_MS) return;
        this.updateHealth({
          sourceId: media.descriptor.id || input.sourceId,
          sourceKind: input.sourceKind,
          label: media.descriptor.label || input.fallbackLabel,
          state: "unavailable",
          stage: "failed",
          level: 0,
          readinessState: "stale",
          errorCode: "source-unavailable",
        });
      }, 1_000);

      const handleTrackEnded = () => {
          this.updateHealth({
            sourceId: media.descriptor.id || input.sourceId,
            sourceKind: input.sourceKind,
            label: media.descriptor.label || input.fallbackLabel,
            state: "unavailable",
            stage: "failed",
            level: 0,
            readinessState: "stale",
            errorCode: "source-unavailable",
          });
      };
      const handleTrackMuted = () => {
        this.updateHealth({
          sourceId: media.descriptor.id || input.sourceId,
          sourceKind: input.sourceKind,
          label: media.descriptor.label || input.fallbackLabel,
          state: "unavailable",
          stage: "failed",
          level: 0,
          readinessState: "stale",
          errorCode: "source-unavailable",
        });
      };
      const tracks = media.stream.getTracks();
      tracks.forEach((track) => {
        track.addEventListener("ended", handleTrackEnded);
        track.addEventListener("mute", handleTrackMuted);
      });

      return {
        sourceKind: input.sourceKind,
        media,
        context,
        node,
        processor,
        lastSignalAtMs: () => lastSignalAtMs,
        calibration: () => ({
          noiseFloor,
          sampleCount: calibrationSampleCount,
          calibratedAtMs: lastCallbackAtMs,
        }),
        release: async (closeMedia) => {
          window.clearInterval(stallTimer);
          tracks.forEach((track) => {
            track.removeEventListener("ended", handleTrackEnded);
            track.removeEventListener("mute", handleTrackMuted);
          });
          processor.onaudioprocess = null;
          processor.disconnect();
          sink.disconnect();
          node.disconnect();
          if (closeMedia) media.close();
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
