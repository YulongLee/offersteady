import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import type { AudioPermission, AudioSourceDescriptor, AudioSourceHealth, CaptureState, CompanionCapabilities } from "@offersteady/protocol";
import type { DesktopNativeRuntimeHealth, DesktopPairingIdentity, DesktopRuntimeConfig, DesktopScreenSource, DesktopScreenshotShortcutSettings } from "./global";
import { MicrophoneAudioAdapter, SystemAudioAdapter, describeMediaError } from "./audio/audio-source-adapter";
import { LocalSourceMonitor } from "./audio/local-source-monitor";
import { DesktopRealtimePublisher, publisherFailureIsTerminal } from "./audio/realtime-publisher";
import appIconUrl from "./assets/app-icon.png";
import { BINDING_LIVE_POLL_MS, desktopPollDelayMs } from "../main/polling-policy";

export const companionStatusCopy: Record<CaptureState, { title: string; detail: string }> = {
  "not-connected": { title: "设备离线", detail: "助手尚未完成服务登记，请检查网络后重试。" },
  "permission-required": { title: "需要系统权限", detail: "请在本助手或操作系统隐私设置中完成麦克风与屏幕录制授权。" },
  ready: { title: "设备在线", detail: "系统授权与本场连接相互独立，输入固定机器码即可连接面试。" },
  capturing: { title: "已连接", detail: "这台电脑正在作为面试伴随终端工作。" },
  paused: { title: "已暂停", detail: "当前没有发送新的音频或屏幕数据。" },
  reconnecting: { title: "正在重连", detail: "请保持网页和伴随程序在线。" },
  error: { title: "连接异常", detail: "请检查后端服务、网页连接码或系统授权。" },
};

export const companionPrimaryAction = (state: CaptureState): string => state === "capturing" ? "已连接" : "复制连接码";

const defaultScreens: readonly DesktopScreenSource[] = [
  { id: "display-1", label: "显示器 1", thumbnailDataUrl: null },
];

const systemAudioOptions: readonly AudioSourceDescriptor[] = [
  { id: "system-loopback", kind: "system", label: "电脑输出音频", available: true },
];

const DEFAULT_MICROPHONE_ID = "default";
export const BINDING_STATUS_POLL_MS = BINDING_LIVE_POLL_MS;

interface ApiEnvelope<T> {
  readonly data: T;
}

interface DesktopActiveBinding {
  readonly bindingGeneration?: number;
  readonly bindingId: string;
  readonly sessionId: string;
  readonly ownerUserId: string;
  readonly deviceId: string;
  readonly manualCode: string;
  readonly displayName: string;
  readonly capabilities: Record<string, unknown>;
  readonly status: "bound" | "stale";
  readonly boundAtMs: number;
  readonly lastSeenAtMs: number;
}

interface DesktopPairingStatus {
  readonly state: "invalid-code" | "not-registered" | "registered" | "stale-bound" | "bound";
  readonly manualCode: string;
  readonly requestedDeviceId?: string | null;
  readonly registered: boolean;
  readonly registeredDeviceId?: string | null;
  readonly bound: boolean;
  readonly sessionStatus?: "preparing" | "live" | "ended" | "missing" | "unknown" | string;
  readonly captureState?: "capturing" | "paused" | "ready" | string;
  readonly message: string;
  readonly staleReason?: string | null;
  readonly authoritative?: boolean;
  readonly leaseVersion?: string | null;
  readonly refreshAfterMs?: number;
  readonly binding?: DesktopActiveBinding | null;
}

export const desktopBindingLeaseIdentity = (binding: DesktopActiveBinding | null) =>
  binding ? `${binding.bindingId}:${binding.bindingGeneration ?? 1}` : "";

export const captureEnabledForBinding = (sessionStatus: string | null, captureState: string | null) =>
  sessionStatus === "live" && captureState !== "paused";

interface DesktopRuntimeStatus {
  readonly sessionId: string;
  readonly sessionStatus: string;
  readonly stage: string;
  readonly deviceRegistered: boolean;
  readonly machineCodeBound: boolean;
  readonly sessionLive: boolean;
  readonly publishers?: readonly unknown[];
  readonly transcriptCount: number;
  readonly sourceHealth?: readonly AudioSourceHealth[];
  readonly frameReceipts?: readonly {
    readonly sourceKind: "microphone" | "system" | "mixed";
    readonly sourceId: string;
    readonly frameCount: number;
    readonly lastFrameAtMs: number;
    readonly lastSequence: number;
    readonly lastAsrStatus: "pending" | "accepted" | "failed";
    readonly lastErrorCode?: string | null;
  }[];
  readonly lastErrorCode?: string | null;
}

const displayedHealthForKind = (
  live: readonly AudioSourceHealth[],
  monitor: readonly AudioSourceHealth[],
  kind: AudioSourceHealth["sourceKind"],
) => {
  const liveEntry = live.find((item) => item.sourceKind === kind);
  const monitorEntry = monitor.find((item) => item.sourceKind === kind);
  if (!liveEntry) return monitorEntry;
  if (!monitorEntry) return liveEntry;
  const liveLooksActive = liveEntry.state === "receiving"
    || liveEntry.state === "silent"
    || (liveEntry.frameCount ?? 0) > 0
    || (liveEntry.backendFrameCount ?? 0) > 0;
  return liveLooksActive ? liveEntry : monitorEntry;
};

const publisherHealthIsActive = (health: AudioSourceHealth) =>
  health.state === "receiving"
  || (health.state === "silent" && (((health.frameCount ?? 0) > 0) || ((health.backendFrameCount ?? 0) > 0)))
  || ((health.frameCount ?? 0) > 0)
  || ((health.backendFrameCount ?? 0) > 0);

export const mergeDisplayedSourceHealth = (
  live: readonly AudioSourceHealth[],
  monitor: readonly AudioSourceHealth[],
): readonly AudioSourceHealth[] => {
  const kinds: readonly AudioSourceHealth["sourceKind"][] = ["microphone", "system"];
  return kinds
    .map((kind) => displayedHealthForKind(live, monitor, kind))
    .filter((item): item is AudioSourceHealth => Boolean(item));
};

export const hasPublisherTakenOver = (live: readonly AudioSourceHealth[]) =>
  live.some((item) => (item.sourceKind === "microphone" || item.sourceKind === "system") && publisherHealthIsActive(item));

const meterPercent = (level: number | undefined) => {
  if (!level || level <= 0) return 0;
  const decibels = 20 * Math.log10(Math.max(level, 0.0001));
  const normalized = (decibels + 54) / 36;
  return Math.max(0, Math.min(100, Math.round(normalized * 100)));
};

const useSmoothedMeterPercent = (level: number | undefined) => {
  const targetRef = useRef(0);
  const [displayLevel, setDisplayLevel] = useState(0);
  targetRef.current = meterPercent(level);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setDisplayLevel(current => {
        const target = targetRef.current;
        const smoothing = target > current ? 0.28 : 0.1;
        const next = current + ((target - current) * smoothing);
        return Math.abs(next - target) < 0.5 ? target : next;
      });
    }, 50);
    return () => window.clearInterval(timer);
  }, []);

  return Math.round(displayLevel);
};

const hasMeaningfulAudioHealth = (health: readonly AudioSourceHealth[]) => health.some((item) =>
  item.state === "receiving"
  || item.state === "silent"
  || (item.frameCount ?? 0) > 0
  || (item.backendFrameCount ?? 0) > 0,
);

const healthCopy = (health: AudioSourceHealth | undefined, label: string, displayLevel?: number) => {
  if (!health) return `${label}等待检测`;
  if (health.state === "receiving") return `${label}收音正常 ${displayLevel ?? meterPercent(health.level)}%`;
  if (health.state === "silent") {
    return label.includes("面试官")
      ? "输出通道已接入，未检测到播放声音"
      : `${label}等待声音`;
  }
  if (health.state === "permission-denied") return `${label}未授权`;
  if (health.errorCode === "adapter-required") return `${label}需要系统音频适配器`;
  if (health.state === "unsupported") return `${label}当前系统不支持`;
  if (health.state === "unavailable") return `${label}不可用`;
  if (health.state === "reconnecting") return `${label}重连中`;
  if (health.state === "error") return `${label}检测异常`;
  return `${label}等待检测`;
};

const permissionFromHealth = (health: AudioSourceHealth | undefined, current: AudioPermission): AudioPermission => {
  if (!health) return current;
  if (health.state === "permission-denied") return "denied";
  if (health.state === "receiving" || health.state === "silent") return "granted";
  return current;
};

const microphonePreferenceScore = (source: AudioSourceDescriptor) => {
  const id = source.id.toLowerCase();
  const label = source.label.toLowerCase();
  if (id === "default" || label.startsWith("default")) return 0;
  if (label.includes("airpods") || label.includes("bluetooth") || label.includes("耳机") || label.includes("headset") || label.includes("headphone")) return 1;
  if (label.includes("macbook") || label.includes("built-in") || label.includes("内建")) return 3;
  return 2;
};

const sortMicrophoneSources = (sources: readonly AudioSourceDescriptor[]) =>
  [...sources].sort((left, right) => microphonePreferenceScore(left) - microphonePreferenceScore(right) || left.label.localeCompare(right.label));

const requestMicrophoneAccessInBackground = async () => {
  if (!window.offersteady?.requestMicrophoneAccess) return false;
  let timeoutId: number | undefined;
  try {
    return await Promise.race([
      window.offersteady.requestMicrophoneAccess(),
      new Promise<boolean>((resolve) => {
        timeoutId = window.setTimeout(() => resolve(false), 2500);
      }),
    ]);
  } finally {
    if (timeoutId !== undefined) window.clearTimeout(timeoutId);
  }
};

const buildRuntimeCaptureNotice = (
  live: boolean,
  runtimeStatus: DesktopRuntimeStatus | null,
  captureDiagnostic: string | null,
  nativeRuntimeReady: boolean,
  nativeRuntimeHealth: DesktopNativeRuntimeHealth | null,
) => {
  if (!live) return null;
  if (captureDiagnostic && (runtimeStatus?.frameReceipts?.length ?? 0) === 0 && (runtimeStatus?.transcriptCount ?? 0) === 0) {
    return captureDiagnostic;
  }
  if ((runtimeStatus?.transcriptCount ?? 0) > 0) return "实时语音已进入后端，并开始同步对话文本";
  if (runtimeStatus?.stage === "publishing" || runtimeStatus?.stage === "transcribing" || (runtimeStatus?.frameReceipts?.length ?? 0) > 0) {
    return "语音正在进入后端，等待实时转写同步到网页";
  }
  if (!nativeRuntimeReady && nativeRuntimeHealth?.ready === false) {
    return "音频链路可继续启动，但原生屏幕采集运行时未就绪；不影响语音转写，截屏回答会受影响";
  }
  return "等待麦克风或电脑输出音频进入实时对话";
};

function normalizeWorkspaceUrl(url: string | undefined) {
  return url || "http://localhost:5173/app";
}

function homeUrl(url: string | undefined) {
  const workspaceUrl = normalizeWorkspaceUrl(url);
  try {
    const parsed = new URL(workspaceUrl);
    parsed.pathname = "/";
    parsed.search = "";
    parsed.hash = "";
    return parsed.toString();
  } catch {
    return "http://localhost:5173/";
  }
}

function guideUrl(url: string | undefined) {
  const workspaceUrl = normalizeWorkspaceUrl(url);
  try {
    const parsed = new URL(workspaceUrl);
    parsed.pathname = "/app/guide";
    parsed.search = "";
    parsed.hash = "";
    return parsed.toString();
  } catch {
    return workspaceUrl;
  }
}

export function liveInterviewUrl(url: string | undefined, sessionId: string) {
  const workspaceUrl = normalizeWorkspaceUrl(url);
  try {
    const parsed = new URL(workspaceUrl);
    parsed.pathname = `/app/interviews/${encodeURIComponent(sessionId)}/live`;
    parsed.search = "";
    parsed.hash = "";
    return parsed.toString();
  } catch {
    return `http://localhost:5173/app/interviews/${encodeURIComponent(sessionId)}/live`;
  }
}

const desktopApiUrl = (runtime: DesktopRuntimeConfig, path: string) => `${runtime.apiBaseUrl.replace(/\/+$/, "")}${path.startsWith("/") ? path : `/${path}`}`;

const desktopBackendFetch = async (runtime: DesktopRuntimeConfig, input: string, init?: RequestInit): Promise<Response> => {
  const url = /^https?:\/\//i.test(input) ? input : desktopApiUrl(runtime, input);
  const headers = new Headers(init?.headers);
  const body = typeof init?.body === "string" ? init.body : init?.body == null ? null : String(init.body);
  if (window.offersteady?.apiRequest) {
    const request: {
      url: string;
      method?: string;
      headers: Record<string, string>;
      body: string | null;
    } = {
      url,
      headers: Object.fromEntries(headers.entries()),
      body,
    };
    if (init?.method) request.method = init.method;
    const result = await window.offersteady.apiRequest(request);
    return new Response(result.bodyText, {
      status: result.status,
      statusText: result.statusText,
      headers: result.headers,
    });
  }
  return fetch(url, init);
};

const readBackendError = async (response: Response) => {
  try {
    const payload = await response.json() as { readonly error?: { readonly message?: string } };
    return payload.error?.message || `HTTP ${response.status}`;
  } catch {
    return `HTTP ${response.status}`;
  }
};

const fetchActiveBinding = async (runtime: DesktopRuntimeConfig, identity: DesktopPairingIdentity) => {
  const byCode = await desktopBackendFetch(runtime, `/realtime-speech/desktop-devices/by-code/${encodeURIComponent(identity.manualCode)}/binding`);
  if (byCode.ok) return byCode;
  if (byCode.status !== 404) return byCode;
  const query = new URLSearchParams({ manualCode: identity.manualCode });
  return desktopBackendFetch(runtime, `/realtime-speech/desktop-devices/${encodeURIComponent(identity.deviceId)}/binding?${query.toString()}`);
};

const fetchPairingStatus = async (runtime: DesktopRuntimeConfig, identity: DesktopPairingIdentity) => {
  const query = new URLSearchParams({
    manualCode: identity.manualCode,
    deviceId: identity.deviceId,
  });
  let response = await desktopBackendFetch(runtime, `/realtime-speech/desktop-devices/${encodeURIComponent(identity.deviceId)}/active-connection?manualCode=${encodeURIComponent(identity.manualCode)}`);
  if (response.status === 404) {
    response = await desktopBackendFetch(runtime, `/realtime-speech/desktop-devices/pairing-status?${query.toString()}`);
  }
  if (!response.ok) throw new Error(await readBackendError(response));
  const envelope = await response.json() as ApiEnvelope<DesktopPairingStatus>;
  return envelope.data;
};

const waitingConnectionInfo = (_runtime?: DesktopRuntimeConfig) =>
  "请打开面试首页，进入面试后输入右侧连接码绑定这台电脑。";

const mergeBackendReceipts = (
  health: readonly AudioSourceHealth[],
  receipts: DesktopRuntimeStatus["frameReceipts"] | undefined,
): readonly AudioSourceHealth[] => {
  if (!receipts?.length) return health;
  return health.map((item) => {
    const receipt = receipts.find(entry => entry.sourceKind === item.sourceKind);
    if (!receipt) return item;
    const merged: AudioSourceHealth = {
      ...item,
      backendFrameCount: receipt.frameCount,
      lastBackendFrameAtMs: receipt.lastFrameAtMs,
      stage: receipt.lastAsrStatus === "accepted" ? "asr-accepted" : "frames-published",
    };
    if (!receipt.lastErrorCode) return merged;
    const errorCode = receipt.lastErrorCode as NonNullable<AudioSourceHealth["errorCode"]>;
    return { ...merged, errorCode };
  });
};

export function CompanionApp() {
  const [state, setState] = useState<CaptureState>("permission-required");
  const [config, setConfig] = useState<DesktopRuntimeConfig | null>(null);
  const [pairingIdentity, setPairingIdentity] = useState<DesktopPairingIdentity | null>(null);
  const [microphoneSources, setMicrophoneSources] = useState<readonly AudioSourceDescriptor[]>([]);
  const [screenSources, setScreenSources] = useState<readonly DesktopScreenSource[]>(defaultScreens);
  const [selectedMicrophoneId, setSelectedMicrophoneId] = useState("");
  const [selectedSystemAudioId, setSelectedSystemAudioId] = useState(systemAudioOptions[0]?.id ?? "");
  const [selectedScreenId, setSelectedScreenId] = useState(defaultScreens[0]?.id ?? "");
  const [permissions, setPermissions] = useState<{ microphone: AudioPermission; systemAudio: AudioPermission }>({ microphone: "unknown", systemAudio: "unknown" });
  const [connectionNotice, setConnectionNotice] = useState("正在生成本机连接码…");
  const [connectionInfo, setConnectionInfo] = useState("暂无连接设备");
  const bindingFailureCountRef = useRef(0);
  const [previewNotice, setPreviewNotice] = useState("选择要捕捉的屏幕");
  const [desktopNotice, setDesktopNotice] = useState("");
  const [screenshotShortcut, setScreenshotShortcut] = useState<DesktopScreenshotShortcutSettings>({
    accelerator: "Control+Shift+Space",
    options: [{ accelerator: "Control+Shift+Space", label: "Control + Shift + Space" }],
  });
  const [screenshotShortcutNotice, setScreenshotShortcutNotice] = useState("仅在已连接并开始面试后生效");
  const [screenshotCaptureLocked, setScreenshotCaptureLocked] = useState(false);
  const [showScreenshotShortcutSettings, setShowScreenshotShortcutSettings] = useState(false);
  const [showScreenPreviewDialog, setShowScreenPreviewDialog] = useState(false);
  const [isScreenPreviewLoading, setIsScreenPreviewLoading] = useState(false);
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [screenCaptureReady, setScreenCaptureReady] = useState(false);
  const [screenPreviewUrl, setScreenPreviewUrl] = useState<string | null>(null);
  const [activeBinding, setActiveBinding] = useState<DesktopActiveBinding | null>(null);
  const [bindingSessionStatus, setBindingSessionStatus] = useState<string | null>(null);
  const [bindingCaptureState, setBindingCaptureState] = useState<string | null>(null);
  const [nativeRuntimeHealth, setNativeRuntimeHealth] = useState<DesktopNativeRuntimeHealth | null>(null);
  const [liveSourceHealthState, setLiveSourceHealthState] = useState<readonly AudioSourceHealth[]>([]);
  const [monitorSourceHealthState, setMonitorSourceHealthState] = useState<readonly AudioSourceHealth[]>([]);
  const [publisherRetryNonce, setPublisherRetryNonce] = useState(0);
  const previewRef = useRef<HTMLVideoElement>(null);
  const previewStream = useRef<MediaStream | null>(null);
  const previewRequestIdRef = useRef(0);
  const publisherRef = useRef<DesktopRealtimePublisher | null>(null);
  const localMonitorRef = useRef<LocalSourceMonitor | null>(null);
  const systemAudioAdapterRef = useRef(new SystemAudioAdapter());
  const sourceHealthRef = useRef<readonly AudioSourceHealth[]>([]);
  const liveSourceHealthRef = useRef<readonly AudioSourceHealth[]>([]);
  const monitorSourceHealthRef = useRef<readonly AudioSourceHealth[]>([]);
  const lastBindingSessionIdRef = useRef<string | null>(null);
  const lastLiveSessionIdRef = useRef<string | null>(null);
  const lastPublisherKickSessionIdRef = useRef<string | null>(null);
  const [webOpenNotice, setWebOpenNotice] = useState("");
  const applyConnectionCopy = (notice: string, info?: string) => {
    setConnectionNotice(current => current === notice ? current : notice);
    if (info !== undefined) {
      setConnectionInfo(current => current === info ? current : info);
    }
  };
  const [captureDiagnostic, setCaptureDiagnostic] = useState<string | null>(null);
  const sourceHealthState = mergeDisplayedSourceHealth(liveSourceHealthState, monitorSourceHealthState);
  const captureEnabled = captureEnabledForBinding(bindingSessionStatus, bindingCaptureState);
  const publisherHasTakenOver = useMemo(
    () => captureEnabled && hasPublisherTakenOver(liveSourceHealthState),
    [captureEnabled, liveSourceHealthState],
  );

  useEffect(() => {
    void window.offersteady?.getScreenshotShortcut?.()
      .then(settings => {
        setScreenshotShortcut(settings);
        setScreenshotShortcutNotice(settings.message ?? (settings.registered ? "快捷键已在系统中生效。" : "快捷键当前未生效，请重新选择。"));
      })
      .catch(() => setScreenshotShortcutNotice("快捷键设置读取失败，请重启助手。"));
    const unsubscribe = window.offersteady?.onScreenshotShortcutNotice?.(message => {
      setScreenshotShortcutNotice(message);
      setDesktopNotice(message);
    });
    return () => unsubscribe?.();
  }, []);

  useEffect(() => {
    let active = true;
    void window.offersteady?.getScreenshotCaptureLock?.()
      .then(lock => {
        if (!active) return;
        setScreenshotCaptureLocked(lock.locked);
        if (lock.locked) setPreviewNotice(lock.message);
      })
      .catch(() => undefined);
    const unsubscribe = window.offersteady?.onScreenshotCaptureLockChanged?.(lock => {
      if (!active) return;
      setScreenshotCaptureLocked(lock.locked);
      setPreviewNotice(lock.locked ? lock.message : "当前截屏已取消，可以重新截屏。");
      if (lock.locked) setDesktopNotice(lock.message);
    });
    return () => {
      active = false;
      unsubscribe?.();
    };
  }, []);

  useEffect(() => {
    liveSourceHealthRef.current = liveSourceHealthState;
    monitorSourceHealthRef.current = monitorSourceHealthState;
    sourceHealthRef.current = sourceHealthState;
  }, [liveSourceHealthState, monitorSourceHealthState, sourceHealthState]);

  const refreshMicrophoneSources = async (preferredId?: string) => {
    const adapter = new MicrophoneAudioAdapter();
    const sources = sortMicrophoneSources(await adapter.listSources().catch(() => [] as AudioSourceDescriptor[]));
    setMicrophoneSources(sources);
    setSelectedMicrophoneId((current) => {
      if (preferredId && sources.some((source) => source.id === preferredId)) return preferredId;
      const defaultSource = sources.find((source) => source.id === DEFAULT_MICROPHONE_ID || source.label.toLowerCase().startsWith("default"));
      if (defaultSource) return defaultSource.id;
      if (current && sources.some((source) => source.id === current)) return current;
      return sources[0]?.id ?? DEFAULT_MICROPHONE_ID;
    });
    return sources;
  };

  useEffect(() => {
    let stopped = false;
    const refreshNativeRuntimeHealth = async () => {
      try {
        const health = await window.offersteady?.getNativeRuntimeHealth?.();
        if (stopped || !health) return;
        setNativeRuntimeHealth(health);
      } catch (error) {
        if (stopped) return;
        setNativeRuntimeHealth({
          available: false,
          ready: false,
          errorCode: "native-runtime-health-failed",
          message: error instanceof Error ? error.message : "原生采集运行时检查失败",
        });
      }
    };
    void refreshNativeRuntimeHealth();
    const timer = window.setInterval(() => void refreshNativeRuntimeHealth(), 5000);
    return () => {
      stopped = true;
      window.clearInterval(timer);
    };
  }, []);

  const effectiveMicrophoneId = selectedMicrophoneId || DEFAULT_MICROPHONE_ID;
  const currentMicrophoneLabel = microphoneSources.find(source => source.id === selectedMicrophoneId)?.label ?? "Default - 当前默认麦克风";
  const currentScreenLabel = screenSources.find(source => source.id === selectedScreenId)?.label ?? "显示器 1";
  const activeScreenshotShortcutLabel = screenshotShortcut.options.find(option => option.accelerator === screenshotShortcut.accelerator)?.label ?? "快捷键设置";
  const microphoneHealth = sourceHealthState.find(item => item.sourceKind === "microphone");
  const systemAudioHealth = sourceHealthState.find(item => item.sourceKind === "system");
  const microphoneMeterLevel = useSmoothedMeterPercent(microphoneHealth?.level);
  const systemAudioMeterLevel = useSmoothedMeterPercent(systemAudioHealth?.level);
const isCaptureSourceReady = (state: AudioSourceHealth["state"] | undefined) =>
  state === "receiving" || state === "silent";
  const microphoneReady = isCaptureSourceReady(microphoneHealth?.state);
  const systemAudioReady = isCaptureSourceReady(systemAudioHealth?.state);
  const screenReady = screenCaptureReady;
  const nativeRuntimeReady = nativeRuntimeHealth?.ready === true;
  const isWindows = config?.platform === "windows";

  const capabilitiesFor = (runtime: DesktopRuntimeConfig): CompanionCapabilities => ({
    protocolVersion: runtime.protocolVersion,
    appVersion: runtime.appVersion,
    platform: runtime.platform,
    architecture: runtime.architecture,
    platformVersion: runtime.platformVersion,
    microphone: microphoneReady ? "granted" : permissions.microphone,
    systemAudio: systemAudioReady ? "granted" : permissions.systemAudio,
    availableSources: [
      ...microphoneSources.map(source => ({ id: source.id, kind: source.kind, label: source.label, available: source.available })),
      ...systemAudioOptions.map(source => ({ id: source.id, kind: source.kind, label: source.label, available: source.available })),
    ],
  });

  const registerDesktopDevice = async (
    identity: DesktopPairingIdentity,
    runtime: DesktopRuntimeConfig,
    nextCapabilities: CompanionCapabilities,
    options?: { silent?: boolean },
  ) => {
    try {
      const response = await desktopBackendFetch(runtime, "/realtime-speech/desktop-devices/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          deviceId: identity.deviceId,
          manualCode: identity.manualCode,
          displayName: identity.displayName,
          capabilities: {
            ...nextCapabilities,
            screenCapture: true,
          },
        }),
      });
      if (!response.ok) {
        throw new Error(await readBackendError(response));
      }
      if (!options?.silent) {
        setState("ready");
        setConnectionNotice("设备在线");
        setConnectionInfo("系统权限已独立保存，等待网页连接本场面试。");
        window.offersteady?.publishCaptureState("ready");
      }
      return true;
    } catch (error) {
      if (!options?.silent) {
        const message = error instanceof Error ? error.message : "后端登记失败";
        setState("not-connected");
        setConnectionNotice("未连接");
        setConnectionInfo(`登记失败：${message}。请确认后端服务已启动后重试。`);
        window.offersteady?.publishCaptureState("not-connected");
      }
      return false;
    }
  };

  useEffect(() => {
    let mounted = true;
    void window.offersteady?.getDesktopConfig().then(async runtime => {
      if (!mounted) return;
      setConfig(runtime);
      const [identity, sources, listedScreens] = await Promise.all([
        window.offersteady.getPairingIdentity(),
        refreshMicrophoneSources(),
        window.offersteady.listScreens?.().catch(() => defaultScreens),
      ]);
      const screens = listedScreens ?? defaultScreens;
      if (!mounted) return;
      setPairingIdentity(identity);
      setScreenSources(screens.length > 0 ? screens : defaultScreens);
      setSelectedScreenId((screens[0] ?? defaultScreens[0])?.id ?? "");
      setConnectionNotice("正在登记这台电脑…");
      await registerDesktopDevice(identity, runtime, {
        protocolVersion: runtime.protocolVersion,
        appVersion: runtime.appVersion,
        platform: runtime.platform,
        architecture: runtime.architecture,
        platformVersion: runtime.platformVersion,
        microphone: permissions.microphone,
        systemAudio: permissions.systemAudio,
        availableSources: [
          ...sources.map(source => ({ id: source.id, kind: source.kind, label: source.label, available: source.available })),
          ...systemAudioOptions.map(source => ({ id: source.id, kind: source.kind, label: source.label, available: true })),
        ],
      });
      void requestMicrophoneAccessInBackground()
        .then(async microphoneGranted => {
          const screenGranted = await window.offersteady?.requestScreenCaptureAccess?.().catch(() => false) ?? false;
          if (!mounted) return;
          setPermissions({
            microphone: microphoneGranted ? "granted" : "denied",
            systemAudio: screenGranted ? "granted" : "denied",
          });
          return refreshMicrophoneSources();
        })
        .catch(() => undefined);
    }).catch(() => {
      if (!mounted) return;
      setConnectionNotice("未连接 | 本机运行信息读取失败，请重新打开伴随程序");
      setConnectionInfo("暂无连接设备");
    });
    return () => {
      mounted = false;
      void localMonitorRef.current?.stop();
      void publisherRef.current?.stop();
      stopPreview();
    };
    // Permissions are intentionally reported as the initial runtime capability here.
    // Runtime permission updates are triggered by actual preview/capture actions.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    void window.offersteady?.setPreferredScreen?.(selectedScreenId || null).catch(() => undefined);
  }, [selectedScreenId]);

  useEffect(() => {
    setScreenCaptureReady(false);
    setScreenPreviewUrl(null);
    setIsPreviewing(false);
    setPreviewNotice(`选择要捕捉的屏幕：${currentScreenLabel}`);
  }, [currentScreenLabel]);

  useEffect(() => {
    const mediaDevices = navigator.mediaDevices;
    if (!mediaDevices?.addEventListener) return;
    const handleDeviceChange = () => {
      void refreshMicrophoneSources();
    };
    mediaDevices.addEventListener("devicechange", handleDeviceChange);
    return () => {
      mediaDevices.removeEventListener("devicechange", handleDeviceChange);
    };
  }, []);

  useEffect(() => {
    if (!config || !pairingIdentity) return;
    let stopped = false;
    let bindingPollInFlight = false;
    let bindingPollTimer: number | null = null;
    let pollAgainWhenSettled = false;
    let consecutivePollFailures = 0;
    const schedulePoll = (delayMs: number) => {
      if (stopped) return;
      if (bindingPollTimer !== null) window.clearTimeout(bindingPollTimer);
      bindingPollTimer = window.setTimeout(() => void pollBindingAndPublishStatus(), delayMs);
    };
    const pollBindingAndPublishStatus = async () => {
      if (stopped) return;
      if (bindingPollInFlight) {
        pollAgainWhenSettled = true;
        return;
      }
      bindingPollInFlight = true;
      let nextDelayMs = desktopPollDelayMs("idle", 0, "binding");
      try {
        let pairingStatus: DesktopPairingStatus;
        try {
          pairingStatus = await fetchPairingStatus(config, pairingIdentity);
        } catch {
          const response = await fetchActiveBinding(config, pairingIdentity);
          if (!response.ok) throw new Error(await readBackendError(response));
          const envelope = await response.json() as ApiEnvelope<DesktopActiveBinding>;
          pairingStatus = {
            state: "bound",
            manualCode: pairingIdentity.manualCode,
            requestedDeviceId: pairingIdentity.deviceId,
            registered: true,
            registeredDeviceId: envelope.data.deviceId,
            bound: true,
            sessionStatus: "unknown",
            message: "网页端已绑定本机。",
            binding: envelope.data,
          };
        }
        consecutivePollFailures = 0;
        bindingFailureCountRef.current = 0;
        if (!pairingStatus.bound || !pairingStatus.binding) {
          if (!stopped) {
            const staleBinding = pairingStatus.state === "stale-bound" && pairingStatus.binding ? pairingStatus.binding : null;
            const nextState: CaptureState = pairingStatus.registered ? "ready" : "not-connected";
            const displayState: CaptureState = staleBinding ? "reconnecting" : nextState;
            setActiveBinding(staleBinding);
            setBindingSessionStatus(null);
            setBindingCaptureState(null);
            setState(displayState);
            const staleCopy = pairingStatus.staleReason === "web-heartbeat-missing"
              ? "网页端绑定已存在，但当前面试页心跳暂未到达；请保持线上实时面试页面打开。"
              : pairingStatus.staleReason === "desktop-heartbeat-stale"
                ? "本地助手心跳过期，正在重新登记这台电脑。"
                : pairingStatus.message ?? waitingConnectionInfo(config);
            applyConnectionCopy(staleBinding ? "已绑定 | 等待网页实时连接" : "设备在线 | 等待面试连接", staleBinding ? staleCopy : "系统权限状态保持不变，请在网页输入固定连接码。");
            window.offersteady?.publishCaptureState(displayState);
          }
          return;
        }
        const binding = pairingStatus.binding;
        const runtimeStatus = null as DesktopRuntimeStatus | null;
        const sessionStatus = runtimeStatus?.sessionStatus ?? pairingStatus.sessionStatus ?? "unknown";
        const live = sessionStatus === "live";
        const captureState = pairingStatus.captureState === "paused" ? "paused" : live ? "capturing" : "ready";
        nextDelayMs = desktopPollDelayMs(live ? "live" : "idle", 0, "binding");
        if (stopped) return;
        setActiveBinding(binding);
        setBindingSessionStatus(sessionStatus);
        setBindingCaptureState(captureState);
        if (lastBindingSessionIdRef.current !== binding.sessionId) {
          lastBindingSessionIdRef.current = binding.sessionId;
          setDesktopNotice("网页面试已绑定这台电脑。");
        }
        if (live && lastLiveSessionIdRef.current !== binding.sessionId) {
          lastLiveSessionIdRef.current = binding.sessionId;
          setDesktopNotice("面试已开始，本地助手正在启动麦克风、电脑输出和屏幕能力。");
        }
        const nextCaptureState: CaptureState = captureState === "paused"
          ? "paused"
          : live
          ? (captureDiagnostic && (runtimeStatus?.frameReceipts?.length ?? 0) === 0 && (runtimeStatus?.transcriptCount ?? 0) === 0 ? "error" : "capturing")
          : "ready";
        setState(nextCaptureState);
        bindingFailureCountRef.current = 0;
        applyConnectionCopy("已连接 | 网页端已绑定本机");
        const runtimeNotice = buildRuntimeCaptureNotice(live, runtimeStatus, captureDiagnostic, nativeRuntimeReady, nativeRuntimeHealth);
        applyConnectionCopy(
          "已连接 | 网页端已绑定本机",
          runtimeNotice
            ? `已绑定面试：${binding.sessionId}，${runtimeNotice}`
            : `已绑定面试：${binding.sessionId}，等待网页端点击开始面试`,
        );
        if (runtimeStatus?.frameReceipts?.length) {
          setLiveSourceHealthState(current => mergeBackendReceipts(current, runtimeStatus?.frameReceipts));
        }
        if ((runtimeStatus?.transcriptCount ?? 0) > 0 || (runtimeStatus?.frameReceipts?.length ?? 0) > 0) {
          setCaptureDiagnostic(null);
        }
        if (
          live
          && !publisherRef.current
          && (runtimeStatus?.publishers?.length ?? 0) === 0
          && lastPublisherKickSessionIdRef.current !== binding.sessionId
        ) {
          lastPublisherKickSessionIdRef.current = binding.sessionId;
          setPublisherRetryNonce((value) => value + 1);
        }
        window.offersteady?.publishCaptureState(nextCaptureState);
        await desktopBackendFetch(config, `/realtime-speech/sessions/${encodeURIComponent(binding.sessionId)}/device-status`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            userId: binding.ownerUserId,
            deviceId: pairingIdentity.deviceId,
            manualCode: pairingIdentity.manualCode,
            captureState,
            sourceHealth: sourceHealthRef.current,
            capabilities: {
              ...capabilitiesFor(config),
              screenCapture: screenReady,
              nativeRuntimeReady,
              nativeRuntimeErrors: nativeRuntimeHealth?.errors ?? [],
            },
          }),
        }).catch(() => undefined);
      } catch (error) {
        if (stopped) return;
        consecutivePollFailures += 1;
        nextDelayMs = desktopPollDelayMs("failure", consecutivePollFailures, "binding");
        bindingFailureCountRef.current += 1;
        if (activeBinding && bindingFailureCountRef.current < 3) return;
        const message = error instanceof Error ? error.message : "绑定状态查询失败";
        setState("not-connected");
        applyConnectionCopy("未连接", `绑定查询失败：${message}。请确认后端服务已启动后重试。`);
        window.offersteady?.publishCaptureState("not-connected");
      } finally {
        bindingPollInFlight = false;
        const delayMs = pollAgainWhenSettled ? 0 : nextDelayMs;
        pollAgainWhenSettled = false;
        schedulePoll(delayMs);
      }
    };
    void pollBindingAndPublishStatus();
    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible") schedulePoll(0);
    };
    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => {
      stopped = true;
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      if (bindingPollTimer !== null) window.clearTimeout(bindingPollTimer);
    };
    // Source health changes several times per second. They must not recreate the
    // binding poller because an in-flight IPC request cannot be cancelled by React.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [config, pairingIdentity]);

  useEffect(() => {
    if (bindingCaptureState === "paused" || captureEnabled || publisherHasTakenOver || !selectedSystemAudioId) {
      void localMonitorRef.current?.stop();
      localMonitorRef.current = null;
      if (bindingCaptureState === "paused" || captureEnabled || publisherHasTakenOver) setMonitorSourceHealthState([]);
      return;
    }
    let cancelled = false;
    const monitor = new LocalSourceMonitor({
      microphoneId: effectiveMicrophoneId,
      systemAudioId: selectedSystemAudioId,
      onHealth: (health) => {
        if (cancelled) return;
        monitorSourceHealthRef.current = health;
        setMonitorSourceHealthState(health);
        sourceHealthRef.current = mergeDisplayedSourceHealth(liveSourceHealthRef.current, health);
        setPermissions((current) => ({
          microphone: permissionFromHealth(health.find((item) => item.sourceKind === "microphone"), current.microphone),
          systemAudio: permissionFromHealth(health.find((item) => item.sourceKind === "system"), current.systemAudio),
        }));
        if (hasMeaningfulAudioHealth(health)) setCaptureDiagnostic(null);
      },
      onFailure: (message) => {
        if (cancelled) return;
        const nextMessage = message.includes("输出音频") || message.includes("系统音频")
          ? `${message}。请先打开腾讯会议/微信通话/浏览器面试页面，并确认对方声音正在这台电脑播放。`
          : message;
        setCaptureDiagnostic(nextMessage);
        if (activeBinding) setConnectionInfo(nextMessage);
      },
    });
    localMonitorRef.current = monitor;
    void monitor.start().catch((error) => {
      if (cancelled) return;
      const message = error instanceof Error ? error.message : "本地音频检测启动失败";
      if (activeBinding) setConnectionInfo(message);
    });
    return () => {
      cancelled = true;
      if (localMonitorRef.current === monitor) localMonitorRef.current = null;
      void monitor.stop();
    };
  }, [bindingCaptureState, captureEnabled, publisherHasTakenOver, effectiveMicrophoneId, selectedSystemAudioId]);

  useEffect(() => {
    if (!config || !pairingIdentity || !activeBinding || !captureEnabled) {
      void publisherRef.current?.stop();
      publisherRef.current = null;
      if (!activeBinding) {
        sourceHealthRef.current = [];
        setLiveSourceHealthState([]);
      }
      return;
    }
    let cancelled = false;
    const publisher = new DesktopRealtimePublisher({
      apiBaseUrl: config.apiBaseUrl,
      binding: {
        sessionId: activeBinding.sessionId,
        ownerUserId: activeBinding.ownerUserId,
        deviceId: pairingIdentity.deviceId,
        manualCode: activeBinding.manualCode,
        displayName: pairingIdentity.displayName,
      },
      microphoneId: effectiveMicrophoneId,
      systemAudioId: selectedSystemAudioId || "system-loopback",
      fetchImpl: (input, init) => desktopBackendFetch(config, String(input), init),
      onHealth: (health) => {
        if (cancelled) return;
        liveSourceHealthRef.current = health;
        sourceHealthRef.current = mergeDisplayedSourceHealth(health, monitorSourceHealthRef.current);
        setLiveSourceHealthState(health);
        setPermissions((current) => ({
          microphone: permissionFromHealth(health.find((item) => item.sourceKind === "microphone"), current.microphone),
          systemAudio: permissionFromHealth(health.find((item) => item.sourceKind === "system"), current.systemAudio),
        }));
        if (hasMeaningfulAudioHealth(health)) setCaptureDiagnostic(null);
      },
      onCaptureState: (captureState) => {
        if (cancelled) return;
        setState(captureState);
        window.offersteady?.publishCaptureState(captureState);
      },
      onFailure: (message) => {
        if (cancelled) return;
        const nextMessage = message.includes("输出音频") || message.includes("系统音频")
          ? `${message}。请先打开腾讯会议/微信通话/浏览器面试页面，并确认对方声音正在这台电脑播放。`
          : message;
        setCaptureDiagnostic(nextMessage);
        setConnectionInfo(nextMessage);
      },
      onServerEvent: (event) => {
        if (cancelled) return;
        if (event.kind === "frame-accepted") {
          setCaptureDiagnostic(null);
          setConnectionInfo("已连接网页端，音频帧正在持续送入后端实时语音链路");
          return;
        }
        if (event.kind === "transcript-updated") {
          setCaptureDiagnostic(null);
          setConnectionInfo("已连接网页端，语音识别正在同步到实时对话");
          return;
        }
        if (event.kind === "degraded") {
          const message = typeof event.payload?.message === "string" ? event.payload.message : "语音识别暂时不可用，正在等待下一段音频";
          setCaptureDiagnostic(message);
          setConnectionInfo(message);
        }
      },
    });
    publisherRef.current = publisher;
    void (async () => {
      const monitor = localMonitorRef.current;
      localMonitorRef.current = null;
      await monitor?.stop();
      if (cancelled) return;
      await publisher.start();
    })().catch((error) => {
        if (cancelled) return;
        const message = error instanceof Error ? error.message : "采集链路启动失败";
        setConnectionInfo(message);
        if (publisherRef.current === publisher) publisherRef.current = null;
        void publisher.stop();
        if (publisherFailureIsTerminal(error)) {
          setConnectionInfo("本场发布通道已失效，正在等待网页重新连接当前设备。");
          return;
        }
        window.setTimeout(() => {
          if (!cancelled) setPublisherRetryNonce((value) => value + 1);
        }, 3_000);
      });
    return () => {
      cancelled = true;
      if (publisherRef.current === publisher) publisherRef.current = null;
      void publisher.stop();
    };
  }, [
    desktopBindingLeaseIdentity(activeBinding),
    activeBinding?.sessionId,
    activeBinding?.ownerUserId,
    activeBinding?.manualCode,
    bindingSessionStatus,
    bindingCaptureState,
    config?.apiBaseUrl,
    pairingIdentity?.deviceId,
    pairingIdentity?.displayName,
    effectiveMicrophoneId,
    selectedSystemAudioId,
    publisherRetryNonce,
  ]);

  useEffect(() => {
    const video = previewRef.current;
    const stream = previewStream.current;
    if (!showScreenPreviewDialog || !isPreviewing || !video || !stream) return;
    video.srcObject = stream;
    video.muted = true;
    video.playsInline = true;
    void video.play().catch(() => undefined);
  }, [isPreviewing, screenPreviewUrl, showScreenPreviewDialog]);

  const stopPreview = () => {
    previewStream.current?.getTracks().forEach(track => track.stop());
    previewStream.current = null;
    if (previewRef.current) previewRef.current.srcObject = null;
    setIsPreviewing(false);
  };

  const closeScreenPreview = () => {
    previewRequestIdRef.current += 1;
    setShowScreenPreviewDialog(false);
    setIsScreenPreviewLoading(false);
    stopPreview();
  };

  const previewScreen = async () => {
    if (screenshotCaptureLocked) {
      setPreviewNotice("上一笔截屏仍在处理中，请稍后再预览。");
      return;
    }
    const requestId = previewRequestIdRef.current + 1;
    previewRequestIdRef.current = requestId;
    stopPreview();
    setScreenPreviewUrl(null);
    setShowScreenPreviewDialog(true);
    setIsScreenPreviewLoading(true);
    setPreviewNotice("正在请求屏幕捕捉权限…");
    try {
      const captured = await window.offersteady.captureCurrentScreen?.(selectedScreenId || null);
      if (requestId !== previewRequestIdRef.current) return;
      if (captured?.errorMessage) throw new Error(captured.errorMessage);
      if (captured?.dataUrl) {
        setScreenPreviewUrl(captured.dataUrl);
        setIsPreviewing(true);
        setIsScreenPreviewLoading(false);
        setScreenCaptureReady(true);
        setPreviewNotice(`屏幕捕捉已就绪：${captured.name || currentScreenLabel}`);
        setDesktopNotice("屏幕预览已获取，本地助手可以处理截图回答。");
        return;
      }
      const opened = await systemAudioAdapterRef.current.openScreenPreview();
      if (requestId !== previewRequestIdRef.current) {
        opened.stream.getTracks().forEach(track => track.stop());
        return;
      }
      previewStream.current = opened.stream;
      setScreenPreviewUrl(null);
      setIsPreviewing(true);
      setIsScreenPreviewLoading(false);
      setScreenCaptureReady(true);
      setPreviewNotice(`屏幕捕捉已就绪：${currentScreenLabel}`);
      setDesktopNotice("屏幕预览已获取，本地助手可以处理截图回答。");
    } catch (error) {
      if (requestId !== previewRequestIdRef.current) return;
      setIsScreenPreviewLoading(false);
      setIsPreviewing(false);
      setScreenCaptureReady(false);
      setPreviewNotice(`屏幕捕捉预览失败：${describeMediaError(error)}`);
      setDesktopNotice(`屏幕捕捉预览失败：${describeMediaError(error)}`);
      if (activeBinding) setConnectionInfo("如已在系统设置中授权，请退出并重新打开伴随程序");
    }
  };

  const updateScreenshotShortcut = async (accelerator: string) => {
    const result = await window.offersteady?.setScreenshotShortcut?.(accelerator);
    if (!result) {
      setScreenshotShortcutNotice("快捷键设置通道不可用，请重启助手。");
      return;
    }
    setScreenshotShortcut(current => ({ ...current, accelerator: result.accelerator }));
    setScreenshotShortcutNotice(result.message);
    setDesktopNotice(result.message);
  };

  const copyConnectionCode = async () => {
    const code = pairingIdentity?.manualCode;
    if (!code) return;
    await navigator.clipboard?.writeText(code).catch(() => undefined);
    setConnectionInfo("连接码已复制");
  };

  const refreshAuthorization = async () => {
    try {
      setState("permission-required");
      setDesktopNotice("正在检查系统权限，机器码和设备身份不会改变…");
      const microphoneGranted = await window.offersteady?.requestMicrophoneAccess().catch(() => false) ?? false;
      const screenGranted = await window.offersteady?.requestScreenCaptureAccess?.().catch(() => false) ?? false;
      setPermissions({
        microphone: microphoneGranted ? "granted" : "denied",
        systemAudio: screenGranted ? "granted" : "denied",
      });
      setDesktopNotice(
        microphoneGranted && screenGranted
          ? "麦克风和屏幕录制权限已就绪。"
          : isWindows
            ? "部分权限尚未开启，请在 Windows 设置 → 隐私和安全性中允许麦克风和屏幕捕捉后重试。"
            : "部分权限尚未开启，请在 macOS 系统设置 → 隐私与安全性中允许后重新检查。",
      );
      setState(activeBinding ? (captureEnabled ? "capturing" : bindingCaptureState === "paused" ? "paused" : "ready") : "ready");
    } catch (error) {
      const message = error instanceof Error ? error.message : "权限检查失败";
      setDesktopNotice(`权限检查失败：${message}`);
      setConnectionInfo(`权限检查失败：${message}`);
      setState("error");
    }
  };

  const openResolvedUrl = async (target: "home" | "workspace" | "guide" | "current-interview") => {
    const configuredWorkspace = normalizeWorkspaceUrl(config?.webWorkspaceUrl);
    const configuredHome = homeUrl(config?.webWorkspaceUrl);
    const configuredGuide = guideUrl(config?.webWorkspaceUrl);
    const configuredCurrentInterview = activeBinding
      ? liveInterviewUrl(config?.webWorkspaceUrl, activeBinding.sessionId)
      : configuredWorkspace;
    const candidates = target === "home"
      ? [configuredHome, "http://localhost:5173/", "http://localhost:4173/", "http://127.0.0.1:5173/", "http://127.0.0.1:4173/"]
      : target === "guide"
        ? [configuredGuide, "http://localhost:5173/app/guide", "http://localhost:4173/app/guide", "http://127.0.0.1:5173/app/guide", "http://127.0.0.1:4173/app/guide"]
        : target === "current-interview" && activeBinding
          ? [
              configuredCurrentInterview,
              liveInterviewUrl("http://localhost:5173/app", activeBinding.sessionId),
              liveInterviewUrl("http://localhost:4173/app", activeBinding.sessionId),
              liveInterviewUrl("http://127.0.0.1:5173/app", activeBinding.sessionId),
              liveInterviewUrl("http://127.0.0.1:4173/app", activeBinding.sessionId),
            ]
          : [configuredWorkspace, "http://localhost:5173/app", "http://localhost:4173/app", "http://127.0.0.1:5173/app", "http://127.0.0.1:4173/app"];
    for (const candidate of candidates) {
      const ok = await window.offersteady?.probeWebUrl(candidate).catch(() => false);
      if (ok) {
        setWebOpenNotice("");
        await window.offersteady?.openExternal(candidate);
        return;
      }
    }
    setWebOpenNotice("本地网页服务还没启动，请先运行 npm run dev:web，再点击打开。");
    if (activeBinding) setConnectionInfo("网页未启动：默认检查了本地开发和预览端口");
  };

  return (
    <main className="companion-shell">
      <header className="mac-window-bar" aria-label="窗口标题">
        <span className="mac-dot close" />
        <span className="mac-dot minimize" />
        <span className="mac-dot zoom" />
        <strong>OfferSteady {config?.appVersion ?? "0.1.0"}</strong>
      </header>

      <section className="companion-terminal" aria-label="面试稳伴随助手">
        <div className="brand-row">
          <img className="brand-icon" src={appIconUrl} alt="面试稳" />
          <h1>面试稳</h1>
        </div>

        <div className="terminal-rows">
          <TerminalRow
            title="麦克风"
            subtitle="识别你的声音"
            statusLabel="我的声音"
            ready={microphoneReady}
            meterLevel={microphoneMeterLevel}
            meterCopy={healthCopy(microphoneHealth, "我的声音", microphoneMeterLevel)}
          >
            <select
              aria-label="选择麦克风"
              value={selectedMicrophoneId}
              onChange={event => {
                const nextId = event.target.value;
                setSelectedMicrophoneId(nextId);
                void refreshMicrophoneSources(nextId);
              }}
              onClick={() => { void refreshMicrophoneSources(selectedMicrophoneId); }}
            >
              {microphoneSources.length === 0 ? (
                <option value={DEFAULT_MICROPHONE_ID}>{currentMicrophoneLabel}</option>
              ) : microphoneSources.map(source => (
                <option key={source.id} value={source.id}>{source.label}</option>
              ))}
            </select>
          </TerminalRow>

          <TerminalRow
            title="电脑输出"
            subtitle="识别你能听到的面试官声音"
            statusLabel="面试官声音"
            ready={systemAudioReady}
            meterLevel={systemAudioMeterLevel}
            meterCopy={healthCopy(systemAudioHealth, "面试官声音", systemAudioMeterLevel)}
          >
            <select
              aria-label="选择系统音频"
              value={selectedSystemAudioId}
              onChange={event => setSelectedSystemAudioId(event.target.value)}
            >
              {systemAudioOptions.map(source => (
                <option key={source.id} value={source.id}>{source.label}</option>
              ))}
            </select>
          </TerminalRow>

          <TerminalRow title="屏幕捕捉" subtitle="选择要捕捉的屏幕" statusLabel="捕捉屏幕" ready={screenReady}>
            <div className="screen-control">
              <select
                aria-label="选择屏幕捕捉来源"
                value={selectedScreenId}
                disabled={screenshotCaptureLocked}
                onChange={event => setSelectedScreenId(event.target.value)}
              >
                {screenSources.map(source => (
                  <option key={source.id} value={source.id}>{source.label}</option>
                ))}
              </select>
              <button
                type="button"
                className="secondary-button"
                disabled={screenshotCaptureLocked}
                onClick={() => { void previewScreen(); }}
              >
                预览
              </button>
              <button type="button" className="secondary-button shortcut-settings-button" onClick={() => setShowScreenshotShortcutSettings(true)}>
                <span>快捷键</span>
                <small>{screenshotShortcut.registered ? activeScreenshotShortcutLabel : "未生效 · 点击设置"}</small>
              </button>
            </div>
          </TerminalRow>
          {showScreenshotShortcutSettings ? (
            <div className="shortcut-settings-backdrop" role="dialog" aria-modal="true" aria-labelledby="shortcut-settings-title">
              <section className="shortcut-settings-sheet">
                <div className="shortcut-settings-head">
                  <div>
                    <span>SCREEN CAPTURE</span>
                    <h2 id="shortcut-settings-title">截屏回答快捷键</h2>
                  </div>
                  <button type="button" aria-label="关闭快捷键设置" onClick={() => setShowScreenshotShortcutSettings(false)}>×</button>
                </div>
                <p>进入并连接正在进行的面试后，即使网页不在前台，也可以直接触发整屏截取和回答。</p>
                <label>
                  <span>快捷键组合</span>
                  <select
                    aria-label="设置截屏回答快捷键"
                    value={screenshotShortcut.accelerator}
                    onChange={event => { void updateScreenshotShortcut(event.target.value); }}
                  >
                    {screenshotShortcut.options.map(option => (
                      <option key={option.accelerator || "disabled"} value={option.accelerator}>{option.label}</option>
                    ))}
                  </select>
                </label>
                <div className="shortcut-settings-notice">{screenshotShortcutNotice}</div>
                <button type="button" className="primary-button" onClick={() => setShowScreenshotShortcutSettings(false)}>完成</button>
              </section>
            </div>
          ) : null}

          {showScreenPreviewDialog ? (
            <div className="screen-preview-backdrop" role="dialog" aria-modal="true" aria-labelledby="screen-preview-title">
              <section className="screen-preview-sheet">
                <header className="screen-preview-head">
                  <div>
                    <span>SCREEN PREVIEW</span>
                    <h2 id="screen-preview-title">屏幕预览 · {currentScreenLabel}</h2>
                  </div>
                  <button type="button" aria-label="关闭屏幕预览" onClick={closeScreenPreview}>×</button>
                </header>
                <p className="screen-preview-notice">{previewNotice}</p>
                <div className="screen-preview-stage" aria-live="polite">
                  {isScreenPreviewLoading ? (
                    <div className="screen-preview-empty"><span className="screen-preview-spinner" />正在获取最新屏幕画面…</div>
                  ) : screenPreviewUrl ? (
                    <img src={screenPreviewUrl} alt={`${currentScreenLabel} 预览`} className="screen-preview-image is-visible" />
                  ) : isPreviewing ? (
                    <video ref={previewRef} className="screen-preview is-visible" />
                  ) : (
                    <div className="screen-preview-empty">{previewNotice}</div>
                  )}
                </div>
                <p className="screen-preview-privacy">仅用于在本机确认当前捕捉范围，不会因预览自动发送到网页端。</p>
                <button type="button" className="primary-button" onClick={closeScreenPreview}>完成</button>
              </section>
            </div>
          ) : null}

          <section className="connection-card" aria-label="连接管理">
            <div className="connection-head">
              <div>
                <h2>连接管理</h2>
                <p>使用固定连接码绑定网页面试</p>
              </div>
              <div className="connection-actions">
                <button type="button" className="code-box" onClick={() => { void copyConnectionCode(); }} aria-label="复制连接码">
                  <span>连接码：</span>
                  <strong>{pairingIdentity?.manualCode ?? "------"}</strong>
                </button>
                <button
                  type="button"
                  className="interview-link-button"
                  onClick={() => { void openResolvedUrl(activeBinding ? "current-interview" : "home"); }}
                >
                  <span className={activeBinding ? "status-light green" : "status-light red"} />
                  <span>{activeBinding ? "进入当前面试" : "打开面试"}</span>
                </button>
              </div>
            </div>
          </section>
        </div>

        <footer className="terminal-footer">
          <button type="button" onClick={() => { void openResolvedUrl("home"); }}>面试稳首页</button>
          <span>|</span>
          <button type="button" onClick={() => { void openResolvedUrl("guide"); }}>使用教程</button>
        </footer>
      </section>
    </main>
  );
}

function TerminalRow(props: {
  readonly title: string;
  readonly subtitle: string;
  readonly statusLabel: string;
  readonly ready: boolean;
  readonly children: ReactNode;
  readonly meterLevel?: number;
  readonly meterCopy?: string;
}) {
  return (
    <section className="terminal-row">
      <div className="row-title">
        <h2>{props.title}</h2>
        <p>{props.subtitle}</p>
        <span className="source-status">
          <SourceLight ready={props.ready} />
          <span>{props.statusLabel}</span>
        </span>
      </div>
      <div className={props.meterCopy ? "row-control has-meter" : "row-control"}>
        <div className="row-control-main">{props.children}</div>
        {props.meterCopy ? (
          <div className="inline-meter-panel" aria-label={`${props.statusLabel}音量条`}>
            <div className="inline-meter-track">
              <div className="inline-meter-fill" style={{ width: `${props.meterLevel ?? 0}%` }} />
            </div>
            <span>{props.meterCopy}</span>
          </div>
        ) : null}
      </div>
    </section>
  );
}

function SourceLight(props: { readonly ready: boolean }) {
  return (
    <span
      className={props.ready ? "source-light green" : "source-light red"}
      title={props.ready ? "已选择可用设备" : "未检测到可用设备"}
      aria-label={props.ready ? "已选择可用设备" : "未检测到可用设备"}
    />
  );
}
