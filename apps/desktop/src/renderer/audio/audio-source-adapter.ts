import type { AudioPermission, AudioSourceDescriptor, AudioSourceKind } from "@offersteady/protocol";

export interface OpenAudioSource {
  readonly descriptor: AudioSourceDescriptor;
  readonly stream: MediaStream;
  close: () => void;
}

export const describeMediaError = (error: unknown): string => {
  if (error instanceof DOMException) {
    if (error.name === "NotAllowedError") return "用户或系统拒绝了权限";
    if (error.name === "NotFoundError") return "没有找到可用设备";
    if (error.name === "NotReadableError") return "设备被其他程序占用或系统暂时不可读";
    if (error.name === "OverconstrainedError") return "当前选择的设备不可用，请切换默认设备";
    if (error.name === "AbortError") return "系统中断了这次测试";
    return `${error.name}: ${error.message || "未知媒体错误"}`;
  }
  if (error instanceof Error) {
    if (error.message === "screen-capture-permission-required") return "电脑输出权限未开启；请在 macOS 系统设置 → 隐私与安全性 → 屏幕与系统音频录制中允许面试稳伴随程序，然后完全退出并重新打开助手";
    if (error.message === "system-audio-unavailable") return "没有拿到电脑输出音频轨道；请确认微信、会议或网页面试声音正在这台电脑播放";
    if (error.message === "media-open-timeout") return "系统没有在限定时间内返回音频流，通常是权限弹窗未处理或屏幕录制权限未开启";
    if (error.message === "screen-video-unavailable") return "没有拿到屏幕视频轨道";
    return error.message;
  }
  return "未知错误";
};

export interface AudioSourceAdapter {
  readonly kind: AudioSourceKind;
  getPermission: () => Promise<AudioPermission>;
  listSources: () => Promise<readonly AudioSourceDescriptor[]>;
  open: (sourceId?: string) => Promise<OpenAudioSource>;
}

export interface MediaDevicesLike {
  enumerateDevices: () => Promise<readonly MediaDeviceInfo[]>;
  getUserMedia: (constraints: MediaStreamConstraints) => Promise<MediaStream>;
  getDisplayMedia: (constraints?: DisplayMediaStreamOptions) => Promise<MediaStream>;
}

export type ScreenCapturePermissionProbe = () => Promise<boolean | undefined>;

const defaultScreenCapturePermissionProbe: ScreenCapturePermissionProbe = async () => {
  if (typeof window === "undefined") return undefined;
  return window.offersteady?.requestScreenCaptureAccess?.().catch(() => false);
};

const closeStream = (stream: MediaStream) => {
  stream.getTracks().forEach((track) => track.stop());
};

const MICROPHONE_ROUTE_ATTEMPT_TIMEOUT_MS = 1_500;

const openMicrophoneStreamWithTimeout = async (
  open: () => Promise<MediaStream>,
  timeoutMs = MICROPHONE_ROUTE_ATTEMPT_TIMEOUT_MS,
): Promise<MediaStream> => {
  let timedOut = false;
  let timeoutId: ReturnType<typeof setTimeout> | undefined;
  const pending = open().then(stream => {
    if (timedOut) {
      closeStream(stream);
      throw new Error("microphone-route-open-timeout");
    }
    return stream;
  });
  try {
    return await Promise.race([
      pending,
      new Promise<MediaStream>((_resolve, reject) => {
        timeoutId = setTimeout(() => {
          timedOut = true;
          reject(new Error("microphone-route-open-timeout"));
        }, timeoutMs);
      }),
    ]);
  } finally {
    if (timeoutId !== undefined) clearTimeout(timeoutId);
  }
};

const preferredMicrophoneConstraints = (sourceId?: string): MediaTrackConstraints => ({
  ...(sourceId ? { deviceId: { exact: sourceId } } : {}),
  channelCount: { ideal: 1 },
  echoCancellation: { ideal: true },
  noiseSuppression: { ideal: true },
  autoGainControl: { ideal: true },
  sampleRate: { ideal: 48_000 },
});

const fallbackMicrophoneConstraints = (sourceId?: string): MediaTrackConstraints => ({
  ...(sourceId ? { deviceId: { ideal: sourceId } } : {}),
  channelCount: { ideal: 1 },
  echoCancellation: { ideal: true },
  noiseSuppression: { ideal: true },
  autoGainControl: { ideal: true },
});

export class MicrophoneAudioAdapter implements AudioSourceAdapter {
  readonly kind = "microphone" as const;

  constructor(private readonly mediaDevices: MediaDevicesLike = navigator.mediaDevices) {}

  async getPermission(): Promise<AudioPermission> {
    try {
      const stream = await this.mediaDevices.getUserMedia({ audio: true, video: false });
      closeStream(stream);
      return "granted";
    } catch (error) {
      return error instanceof DOMException && error.name === "NotAllowedError" ? "denied" : "prompt";
    }
  }

  async listSources(): Promise<readonly AudioSourceDescriptor[]> {
    const devices = await this.mediaDevices.enumerateDevices();
    return devices
      .filter((device) => device.kind === "audioinput")
      .map((device, index) => ({
        id: device.deviceId || `microphone-${index}`,
        kind: this.kind,
        label: device.label || `麦克风 ${index + 1}`,
        available: true,
      }));
  }

  async open(sourceId?: string): Promise<OpenAudioSource> {
    const normalizedSourceId = sourceId === "default" ? undefined : sourceId;
    const openDefaultMicrophone = async () => {
      const stream = await this.mediaDevices.getUserMedia({ audio: true, video: false });
      if (stream.getAudioTracks().length === 0) {
        closeStream(stream);
        throw new Error("microphone-audio-unavailable");
      }
      return stream;
    };
    const openWithConstraints = async (constraints: MediaTrackConstraints) => {
      const stream = await this.mediaDevices.getUserMedia({
        audio: constraints,
        video: false,
      });
      if (stream.getAudioTracks().length === 0) {
        closeStream(stream);
        throw new Error("microphone-audio-unavailable");
      }
      return stream;
    };

    let stream: MediaStream;
    try {
      stream = normalizedSourceId
        ? await openWithConstraints(preferredMicrophoneConstraints(normalizedSourceId))
        : await openWithConstraints(preferredMicrophoneConstraints());
    } catch (error) {
      try {
        stream = await openWithConstraints(fallbackMicrophoneConstraints(normalizedSourceId));
      } catch {
        const devices = await this.mediaDevices.enumerateDevices().catch(() => []);
        const candidates = devices
          .filter(device => device.kind === "audioinput" && device.deviceId && device.deviceId !== "default" && device.deviceId !== normalizedSourceId)
          .map(device => device.deviceId);
        let lastError: unknown = error;
        for (const candidate of candidates) {
          try {
            stream = await openWithConstraints(fallbackMicrophoneConstraints(candidate));
            lastError = null;
            break;
          } catch (candidateError) {
            lastError = candidateError;
          }
        }
        if (!stream!) {
          try {
            stream = await openDefaultMicrophone();
          } catch {
            throw lastError ?? error;
          }
        }
      }
    }
    return this.describeOpenStream(stream, normalizedSourceId);
  }

  async openFallback(excludedSourceId?: string): Promise<OpenAudioSource> {
    const devices = await this.mediaDevices.enumerateDevices().catch(() => []);
    const candidates = devices
      .filter(device => (
        device.kind === "audioinput"
        && Boolean(device.deviceId)
        && device.deviceId !== "default"
        && device.deviceId !== excludedSourceId
      ))
      .sort((left, right) => {
        const builtIn = /macbook|built[- ]?in|内建|内置/i;
        return Number(builtIn.test(right.label)) - Number(builtIn.test(left.label));
      });
    let lastError: unknown = new Error("microphone-audio-unavailable");
    for (const candidate of candidates) {
      try {
        const stream = await openMicrophoneStreamWithTimeout(() => this.mediaDevices.getUserMedia({
          audio: preferredMicrophoneConstraints(candidate.deviceId),
          video: false,
        }));
        if (stream.getAudioTracks().length === 0) {
          closeStream(stream);
          continue;
        }
        return this.describeOpenStream(stream, candidate.deviceId);
      } catch (error) {
        lastError = error;
      }
    }
    try {
      const stream = await openMicrophoneStreamWithTimeout(() => this.mediaDevices.getUserMedia({
        audio: fallbackMicrophoneConstraints(),
        video: false,
      }));
      if (stream.getAudioTracks().length === 0) {
        closeStream(stream);
        throw new Error("microphone-audio-unavailable");
      }
      return this.describeOpenStream(stream);
    } catch (error) {
      throw lastError instanceof Error ? lastError : error;
    }
  }

  private describeOpenStream(stream: MediaStream, normalizedSourceId?: string): OpenAudioSource {
    const audioTrack = stream.getAudioTracks()[0];
    const trackSettings = audioTrack && typeof audioTrack.getSettings === "function" ? audioTrack.getSettings() : undefined;
    const descriptor: AudioSourceDescriptor = {
      id: trackSettings?.deviceId ?? normalizedSourceId ?? audioTrack?.id ?? "microphone-default",
      kind: this.kind,
      label: audioTrack?.label || "默认麦克风",
      available: true,
    };
    return { descriptor, stream, close: () => closeStream(stream) };
  }
}

export class SystemAudioAdapter implements AudioSourceAdapter {
  readonly kind = "system" as const;

  constructor(
    private readonly mediaDevices: MediaDevicesLike = navigator.mediaDevices,
    private readonly permissionProbe: ScreenCapturePermissionProbe = defaultScreenCapturePermissionProbe,
  ) {}

  async getPermission(): Promise<AudioPermission> {
    const granted = await this.permissionProbe();
    if (granted === undefined) return "prompt";
    return granted ? "granted" : "denied";
  }

  async listSources(): Promise<readonly AudioSourceDescriptor[]> {
    return [{ id: "system-loopback", kind: this.kind, label: "电脑输出音频", available: true }];
  }

  async open(): Promise<OpenAudioSource> {
    const granted = await this.permissionProbe();
    if (granted === false) throw new Error("screen-capture-permission-required");
    const openStandardCapture = () => this.mediaDevices.getDisplayMedia({
      audio: true,
      video: true,
    });
    let stream: MediaStream;
    try {
      stream = await this.mediaDevices.getDisplayMedia({
        audio: true,
        video: { frameRate: 1, width: 2, height: 2 },
      });
    } catch {
      stream = await openStandardCapture();
    }
    if (stream.getAudioTracks().length === 0) {
      closeStream(stream);
      stream = await openStandardCapture();
      if (stream.getAudioTracks().length === 0) {
        closeStream(stream);
        throw new Error("system-audio-unavailable");
      }
    }
    stream.getVideoTracks().forEach((track) => track.stop());

    const descriptor: AudioSourceDescriptor = {
      id: "system-loopback",
      kind: this.kind,
      label: "电脑输出音频",
      available: true,
    };
    return { descriptor, stream, close: () => closeStream(stream) };
  }

  async openScreenPreview(): Promise<OpenAudioSource> {
    const stream = await this.mediaDevices.getDisplayMedia({
      audio: false,
      video: { frameRate: 8 },
    });
    if (stream.getVideoTracks().length === 0) {
      closeStream(stream);
      throw new Error("screen-video-unavailable");
    }
    const descriptor: AudioSourceDescriptor = {
      id: stream.getVideoTracks()[0]?.id ?? "screen-preview",
      kind: this.kind,
      label: "屏幕捕捉",
      available: true,
    };
    return { descriptor, stream, close: () => closeStream(stream) };
  }
}
