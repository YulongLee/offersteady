import { useEffect, useRef, useState, type ReactNode } from "react";
import type { AudioPermission, AudioSourceDescriptor, AudioSourceHealth, CaptureState, CompanionCapabilities } from "@offersteady/protocol";
import type { DesktopNativeRuntimeHealth, DesktopPairingIdentity, DesktopRuntimeConfig, DesktopScreenSource } from "./global";
import { MicrophoneAudioAdapter, SystemAudioAdapter, describeMediaError } from "./audio/audio-source-adapter";
import { LocalSourceMonitor } from "./audio/local-source-monitor";
import { DesktopRealtimePublisher } from "./audio/realtime-publisher";
import appIconUrl from "./assets/app-icon.png";

export const companionStatusCopy: Record<CaptureState, { title: string; detail: string }> = {
  "not-connected": { title: "未连接", detail: "请打开面试稳网页，开始面试后输入连接码。" },
  "permission-required": { title: "等待连接", detail: "选择麦克风、系统音频和屏幕捕捉后，在网页端输入连接码。" },
  ready: { title: "等待网页连接", detail: "连接码已生成。网页或手机端输入后，会绑定这台收音电脑。" },
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
const BINDING_STATUS_POLL_MS = 2500;

interface ApiEnvelope<T> {
  readonly data: T;
}

interface DesktopActiveBinding {
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
  readonly message: string;
  readonly staleReason?: string | null;
  readonly binding?: DesktopActiveBinding | null;
}

interface DesktopRuntimeStatus {
  readonly sessionId: string;
  readonly sessionStatus: string;
  readonly stage: string;
  readonly deviceRegistered: boolean;
  readonly machineCodeBound: boolean;
  readonly sessionLive: boolean;
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

interface RemoteScreenshotCaptureRequest {
  readonly requestId: string;
  readonly sessionId: string;
  readonly ownerUserId: string;
  readonly deviceId: string;
  readonly manualCode: string;
  readonly instruction: string;
  readonly status: "requested" | "processing" | "completed" | "failed" | "cancelled";
  readonly answerTaskId?: string | null;
  readonly errorMessage?: string | null;
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
  return Math.max(4, Math.min(100, Math.round((level / 0.04) * 100)));
};

const hasMeaningfulAudioHealth = (health: readonly AudioSourceHealth[]) => health.some((item) =>
  item.state === "receiving"
  || item.state === "silent"
  || (item.frameCount ?? 0) > 0
  || (item.backendFrameCount ?? 0) > 0,
);

const healthCopy = (health: AudioSourceHealth | undefined, label: string) => {
  if (!health) return `${label}等待检测`;
  if (health.state === "receiving") return `${label}收音正常 ${meterPercent(health.level)}%`;
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
  const response = await desktopBackendFetch(runtime, `/realtime-speech/desktop-devices/pairing-status?${query.toString()}`);
  if (!response.ok) throw new Error(await readBackendError(response));
  const envelope = await response.json() as ApiEnvelope<DesktopPairingStatus>;
  return envelope.data;
};

const waitingConnectionInfo = (_runtime?: DesktopRuntimeConfig) =>
  "请打开面试首页，进入面试后输入右侧连接码绑定这台电脑。";

const fetchRuntimeStatus = async (runtime: DesktopRuntimeConfig, binding: DesktopActiveBinding) => {
  const query = new URLSearchParams({ userId: binding.ownerUserId });
  const response = await desktopBackendFetch(runtime, `/realtime-speech/sessions/${encodeURIComponent(binding.sessionId)}/runtime?${query.toString()}`);
  if (!response.ok) throw new Error(await readBackendError(response));
  const envelope = await response.json() as ApiEnvelope<DesktopRuntimeStatus>;
  return envelope.data;
};

const fetchNextRemoteScreenshotCaptureRequest = async (runtime: DesktopRuntimeConfig, identity: DesktopPairingIdentity) => {
  const query = new URLSearchParams({ manualCode: identity.manualCode });
  const response = await desktopBackendFetch(runtime, `/screenshot-answer/desktop-devices/${encodeURIComponent(identity.deviceId)}/capture-requests/next?${query.toString()}`);
  if (!response.ok) {
    if (response.status === 404) return null;
    throw new Error(await readBackendError(response));
  }
  const envelope = await response.json() as ApiEnvelope<RemoteScreenshotCaptureRequest | null>;
  return envelope.data;
};

const uploadRemoteScreenshotCapture = async (
  runtime: DesktopRuntimeConfig,
  identity: DesktopPairingIdentity,
  requestId: string,
  screenshot: { readonly dataUrl?: string; readonly name?: string; readonly extension?: string },
) => {
  if (!screenshot.dataUrl) throw new Error("本地助手未获取到有效截图");
  const [meta, payload] = screenshot.dataUrl.split(",", 2);
  if (!meta || !payload) throw new Error("本地助手未返回可上传的截图数据");
  const mimeType = meta.match(/^data:(.*?);base64$/)?.[1] || "";
  const extension = screenshot.extension || (mimeType === "image/jpeg" ? "jpg" : mimeType === "image/webp" ? "webp" : "png");
  const filename = `${(screenshot.name || "current-screen").replace(/[\\/:*?\"<>|]+/g, "-")}.${extension}`;
  const uploadUrl = desktopApiUrl(runtime, `/screenshot-answer/capture-requests/${encodeURIComponent(requestId)}/desktop-upload`);
  const result = await window.offersteady.uploadScreenshotCapture?.({
    url: uploadUrl,
    deviceId: identity.deviceId,
    manualCode: identity.manualCode,
    dataUrl: screenshot.dataUrl,
    filename,
  });
  if (!result) throw new Error("本地助手上传通道不可用，请重启伴随程序。");
  const response = new Response(result.bodyText, {
    status: result.status,
    statusText: result.statusText,
    headers: result.headers,
  });
  if (!response.ok) throw new Error(await readBackendError(response));
  return response.json();
};

const failRemoteScreenshotCapture = async (
  runtime: DesktopRuntimeConfig,
  identity: DesktopPairingIdentity,
  requestId: string,
  message: string,
  stage = "capture-failed",
) => {
  await desktopBackendFetch(runtime, `/screenshot-answer/capture-requests/${encodeURIComponent(requestId)}/desktop-fail`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      deviceId: identity.deviceId,
      manualCode: identity.manualCode,
      message,
      stage,
    }),
  });
};

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
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [screenCaptureReady, setScreenCaptureReady] = useState(false);
  const [screenPreviewUrl, setScreenPreviewUrl] = useState<string | null>(null);
  const [activeBinding, setActiveBinding] = useState<DesktopActiveBinding | null>(null);
  const [bindingSessionStatus, setBindingSessionStatus] = useState<string | null>(null);
  const [nativeRuntimeHealth, setNativeRuntimeHealth] = useState<DesktopNativeRuntimeHealth | null>(null);
  const [liveSourceHealthState, setLiveSourceHealthState] = useState<readonly AudioSourceHealth[]>([]);
  const [monitorSourceHealthState, setMonitorSourceHealthState] = useState<readonly AudioSourceHealth[]>([]);
  const previewRef = useRef<HTMLVideoElement>(null);
  const previewStream = useRef<MediaStream | null>(null);
  const publisherRef = useRef<DesktopRealtimePublisher | null>(null);
  const localMonitorRef = useRef<LocalSourceMonitor | null>(null);
  const systemAudioAdapterRef = useRef(new SystemAudioAdapter());
  const sourceHealthRef = useRef<readonly AudioSourceHealth[]>([]);
  const liveSourceHealthRef = useRef<readonly AudioSourceHealth[]>([]);
  const monitorSourceHealthRef = useRef<readonly AudioSourceHealth[]>([]);
  const processingScreenshotRequestIdRef = useRef<string | null>(null);
  const completedScreenshotRequestIdsRef = useRef<Set<string>>(new Set());
  const lastBindingSessionIdRef = useRef<string | null>(null);
  const lastLiveSessionIdRef = useRef<string | null>(null);
  const [webOpenNotice, setWebOpenNotice] = useState("");
  const applyConnectionCopy = (notice: string, info?: string) => {
    setConnectionNotice(current => current === notice ? current : notice);
    if (info !== undefined) {
      setConnectionInfo(current => current === info ? current : info);
    }
  };
  const [captureDiagnostic, setCaptureDiagnostic] = useState<string | null>(null);
  const sourceHealthState = mergeDisplayedSourceHealth(liveSourceHealthState, monitorSourceHealthState);

  useEffect(() => {
    liveSourceHealthRef.current = liveSourceHealthState;
    monitorSourceHealthRef.current = monitorSourceHealthState;
    sourceHealthRef.current = sourceHealthState;
  }, [liveSourceHealthState, monitorSourceHealthState, sourceHealthState]);

  const refreshMicrophoneSources = async (preferredId?: string) => {
    const adapter = new MicrophoneAudioAdapter();
    const sources = await adapter.listSources().catch(() => [] as AudioSourceDescriptor[]);
    setMicrophoneSources(sources);
    setSelectedMicrophoneId((current) => {
      if (preferredId && sources.some((source) => source.id === preferredId)) return preferredId;
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
  const currentScreenPreview = screenSources.find(source => source.id === selectedScreenId)?.thumbnailDataUrl ?? null;
  const microphoneHealth = sourceHealthState.find(item => item.sourceKind === "microphone");
  const systemAudioHealth = sourceHealthState.find(item => item.sourceKind === "system");
const isCaptureSourceReady = (state: AudioSourceHealth["state"] | undefined) =>
  state === "receiving" || state === "silent";
  const microphoneReady = isCaptureSourceReady(microphoneHealth?.state);
  const systemAudioReady = isCaptureSourceReady(systemAudioHealth?.state);
  const screenReady = screenCaptureReady;
  const nativeRuntimeReady = nativeRuntimeHealth?.ready === true;

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
        setConnectionNotice("未连接");
        setConnectionInfo(waitingConnectionInfo(runtime));
        window.offersteady?.publishCaptureState("ready");
      }
      return true;
    } catch (error) {
      if (!options?.silent) {
        const message = error instanceof Error ? error.message : "后端登记失败";
        setState("permission-required");
        setConnectionNotice("未连接");
        setConnectionInfo(`登记失败：${message}。请确认后端服务已启动后重试。`);
        window.offersteady?.publishCaptureState("permission-required");
      }
      return false;
    }
  };

  useEffect(() => {
    let mounted = true;
    void window.offersteady?.getDesktopConfig().then(async runtime => {
      if (!mounted) return;
      setConfig(runtime);
      await window.offersteady?.requestMicrophoneAccess().catch(() => false);
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
    setScreenPreviewUrl(currentScreenPreview);
    setIsPreviewing(Boolean(currentScreenPreview));
    setPreviewNotice(currentScreenPreview ? `已获取缩略图，请点击预览验证屏幕捕捉：${currentScreenLabel}` : `选择要捕捉的屏幕：${currentScreenLabel}`);
  }, [currentScreenLabel, currentScreenPreview]);

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
    const syncRegistration = async (silent: boolean) => {
      const ok = await registerDesktopDevice(pairingIdentity, config, {
        ...capabilitiesFor(config),
      }, { silent });
      if (stopped) return;
      if (!ok) {
        if (!activeBinding) {
          setState("reconnecting");
          setConnectionNotice("未连接 | 后端登记失败");
          setConnectionInfo("请确认后端服务已启动后重试。");
          window.offersteady?.publishCaptureState("reconnecting");
        }
        return;
      }
      if (!activeBinding) {
        setConnectionNotice("未连接");
        setConnectionInfo(waitingConnectionInfo(config));
      }
    };
    void syncRegistration(true);
    const interval = window.setInterval(() => { void syncRegistration(true); }, 10000);
    return () => {
      stopped = true;
      window.clearInterval(interval);
    };
  }, [config, pairingIdentity, microphoneSources, permissions, activeBinding, selectedMicrophoneId, selectedSystemAudioId]);

  useEffect(() => {
    if (!config || !pairingIdentity || !activeBinding) return;
    let stopped = false;
    const pollRemoteScreenshotRequests = async () => {
      if (processingScreenshotRequestIdRef.current) return;
      try {
        const request = await fetchNextRemoteScreenshotCaptureRequest(config, pairingIdentity);
        if (stopped || !request) return;
        if (request.status === "completed" || request.status === "failed" || completedScreenshotRequestIdsRef.current.has(request.requestId)) return;
        processingScreenshotRequestIdRef.current = request.requestId;
        setPreviewNotice("网页端已发起截图回答，正在由本地助手截取你选择的共享屏幕…");
        setDesktopNotice("网页端已请求截图回答，本地助手正在截取当前选择的屏幕。");
        if (selectedScreenId && !screenSources.some((source) => source.id === selectedScreenId)) {
          throw new Error("当前选择的屏幕源已经不可用，请在本地助手中重新选择显示器后再试。");
        }
        const capture = await window.offersteady.captureCurrentScreen?.(selectedScreenId || null);
        if (capture?.errorMessage) throw new Error(capture.errorMessage);
        if (!capture?.dataUrl) throw new Error("本地助手未获取到有效共享屏幕画面，请检查屏幕捕捉权限。");
        await uploadRemoteScreenshotCapture(config, pairingIdentity, request.requestId, capture);
        completedScreenshotRequestIdsRef.current.add(request.requestId);
        setPreviewNotice("本地助手已完成本次截图，并已回传后端进行识别回答");
        setDesktopNotice("截图已回传网页端，正在生成截图回答。");
      } catch (error) {
        if (!stopped) {
          const message = error instanceof Error ? error.message : "本地助手执行截图回答失败";
          if (processingScreenshotRequestIdRef.current) {
            void failRemoteScreenshotCapture(config, pairingIdentity, processingScreenshotRequestIdRef.current, message, message.includes("上传") ? "upload-failed" : "capture-failed").catch(() => undefined);
          }
          setPreviewNotice(message);
          setDesktopNotice(`截图失败：${message}`);
        }
      } finally {
        processingScreenshotRequestIdRef.current = null;
      }
    };
    void pollRemoteScreenshotRequests();
    const timer = window.setInterval(() => {
      void pollRemoteScreenshotRequests();
    }, 1200);
    return () => {
      stopped = true;
      window.clearInterval(timer);
    };
  }, [config, pairingIdentity, activeBinding, selectedScreenId]);

  useEffect(() => {
    if (!config || !pairingIdentity) return;
    let stopped = false;
    const pollBindingAndPublishStatus = async () => {
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
        if (!pairingStatus.bound || !pairingStatus.binding) {
          if (!stopped) {
            const nextState: CaptureState = pairingStatus.registered ? "ready" : "not-connected";
            setActiveBinding(null);
            setBindingSessionStatus(null);
            setState(nextState);
            applyConnectionCopy(
              "未连接",
              waitingConnectionInfo(config),
            );
            window.offersteady?.publishCaptureState(nextState);
          }
          return;
        }
        const binding = pairingStatus.binding;
        let runtimeStatus: DesktopRuntimeStatus | null = null;
        try {
          runtimeStatus = await fetchRuntimeStatus(config, binding);
        } catch {
          runtimeStatus = null;
        }
        const sessionStatus = runtimeStatus?.sessionStatus ?? pairingStatus.sessionStatus ?? "unknown";
        const live = sessionStatus === "live";
        if (stopped) return;
        setActiveBinding(binding);
        setBindingSessionStatus(sessionStatus);
        if (lastBindingSessionIdRef.current !== binding.sessionId) {
          lastBindingSessionIdRef.current = binding.sessionId;
          setDesktopNotice("网页面试已绑定这台电脑。");
        }
        if (live && lastLiveSessionIdRef.current !== binding.sessionId) {
          lastLiveSessionIdRef.current = binding.sessionId;
          setDesktopNotice("面试已开始，本地助手正在启动麦克风、电脑输出和屏幕能力。");
        }
        const nextCaptureState: CaptureState = live
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
        window.offersteady?.publishCaptureState(nextCaptureState);
        await desktopBackendFetch(config, `/realtime-speech/sessions/${encodeURIComponent(binding.sessionId)}/device-status`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            userId: binding.ownerUserId,
            deviceId: pairingIdentity.deviceId,
            captureState: live ? "capturing" : "connected",
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
        bindingFailureCountRef.current += 1;
        if (activeBinding && bindingFailureCountRef.current < 3) return;
        const message = error instanceof Error ? error.message : "绑定状态查询失败";
        setState("not-connected");
        applyConnectionCopy("未连接", `绑定查询失败：${message}。请确认后端服务已启动后重试。`);
        window.offersteady?.publishCaptureState("not-connected");
      }
    };
    void pollBindingAndPublishStatus();
    const interval = window.setInterval(() => void pollBindingAndPublishStatus(), BINDING_STATUS_POLL_MS);
    return () => {
      stopped = true;
      window.clearInterval(interval);
    };
  }, [captureDiagnostic, config, pairingIdentity, selectedMicrophoneId, selectedSystemAudioId, microphoneSources, permissions, screenReady, nativeRuntimeReady, nativeRuntimeHealth]);

  useEffect(() => {
    const publisherHasTakenOver = bindingSessionStatus === "live"
      && hasPublisherTakenOver(liveSourceHealthState);
    if (publisherHasTakenOver || !selectedSystemAudioId) {
      void localMonitorRef.current?.stop();
      localMonitorRef.current = null;
      if (publisherHasTakenOver) setMonitorSourceHealthState([]);
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
  }, [bindingSessionStatus, liveSourceHealthState, effectiveMicrophoneId, selectedSystemAudioId]);

  useEffect(() => {
    if (!config || !pairingIdentity || !activeBinding || bindingSessionStatus !== "live") {
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
    void publisher.start().catch((error) => {
      if (cancelled) return;
      const message = error instanceof Error ? error.message : "采集链路启动失败";
      setConnectionInfo(message);
    });
    return () => {
      cancelled = true;
      if (publisherRef.current === publisher) publisherRef.current = null;
      void publisher.stop();
    };
  }, [activeBinding?.sessionId, activeBinding?.ownerUserId, bindingSessionStatus, config, pairingIdentity, effectiveMicrophoneId, selectedSystemAudioId]);

  useEffect(() => {
    const video = previewRef.current;
    const stream = previewStream.current;
    if (!isPreviewing || !video || !stream) return;
    video.srcObject = stream;
    video.muted = true;
    video.playsInline = true;
    void video.play().catch(() => undefined);
  }, [isPreviewing, screenPreviewUrl]);

  const stopPreview = () => {
    previewStream.current?.getTracks().forEach(track => track.stop());
    previewStream.current = null;
    if (previewRef.current) previewRef.current.srcObject = null;
    setIsPreviewing(Boolean(screenPreviewUrl));
  };

  const previewScreen = async () => {
    stopPreview();
    setPreviewNotice("正在请求屏幕捕捉权限…");
    try {
      const captured = await window.offersteady.captureCurrentScreen?.(selectedScreenId || null);
      if (captured?.errorMessage) throw new Error(captured.errorMessage);
      if (captured?.dataUrl) {
        setScreenPreviewUrl(captured.dataUrl);
        setIsPreviewing(true);
        setScreenCaptureReady(true);
        setPreviewNotice(`屏幕捕捉已就绪：${captured.name || currentScreenLabel}`);
        setDesktopNotice("屏幕预览已获取，本地助手可以处理截图回答。");
        return;
      }
      const opened = await systemAudioAdapterRef.current.openScreenPreview();
      previewStream.current = opened.stream;
      setScreenPreviewUrl(null);
      setIsPreviewing(true);
      setScreenCaptureReady(true);
      setPreviewNotice(`屏幕捕捉已就绪：${currentScreenLabel}`);
      setDesktopNotice("屏幕预览已获取，本地助手可以处理截图回答。");
    } catch (error) {
      setScreenCaptureReady(false);
      setPreviewNotice(`屏幕捕捉预览失败：${describeMediaError(error)}`);
      setDesktopNotice(`屏幕捕捉预览失败：${describeMediaError(error)}`);
      if (activeBinding) setConnectionInfo("如已在系统设置中授权，请退出并重新打开伴随程序");
    }
  };

  const copyConnectionCode = async () => {
    const code = pairingIdentity?.manualCode;
    if (!code) return;
    await navigator.clipboard?.writeText(code).catch(() => undefined);
    setConnectionInfo("连接码已复制");
  };

  const resetAuthorization = async () => {
    try {
      setState("permission-required");
      setDesktopNotice("正在重置授权并重新生成设备码…");
      setConnectionNotice("未连接");
      setConnectionInfo("正在重置本机授权，请稍候");
      await window.offersteady?.requestMicrophoneAccess().catch(() => false);
      await window.offersteady?.resetPairingIdentity?.();
      window.location.reload();
    } catch (error) {
      const message = error instanceof Error ? error.message : "重新授权失败";
      setDesktopNotice(`重新授权失败：${message}`);
      setConnectionInfo(`重新授权失败：${message}`);
      setState("error");
    }
  };

  const openResolvedUrl = async (target: "home" | "workspace" | "guide") => {
    const configuredWorkspace = normalizeWorkspaceUrl(config?.webWorkspaceUrl);
    const configuredHome = homeUrl(config?.webWorkspaceUrl);
    const configuredGuide = guideUrl(config?.webWorkspaceUrl);
    const candidates = target === "home"
      ? [configuredHome, "http://localhost:5173/", "http://localhost:4173/", "http://127.0.0.1:5173/", "http://127.0.0.1:4173/"]
      : target === "guide"
        ? [configuredGuide, "http://localhost:5173/app/guide", "http://localhost:4173/app/guide", "http://127.0.0.1:5173/app/guide", "http://127.0.0.1:4173/app/guide"]
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
            meterLevel={meterPercent(microphoneHealth?.level)}
            meterCopy={healthCopy(microphoneHealth, "我的声音")}
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
            meterLevel={meterPercent(systemAudioHealth?.level)}
            meterCopy={healthCopy(systemAudioHealth, "面试官声音")}
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
                onChange={event => setSelectedScreenId(event.target.value)}
              >
                {screenSources.map(source => (
                  <option key={source.id} value={source.id}>{source.label}</option>
                ))}
              </select>
              <button type="button" className="secondary-button" onClick={() => { void previewScreen(); }}>预览</button>
            </div>
          </TerminalRow>

          <section className="preview-row" aria-label="屏幕捕捉预览">
            <div>
              <strong>{currentScreenLabel}</strong>
              <span>{previewNotice}</span>
            </div>
            {screenPreviewUrl ? (
              <img
                src={screenPreviewUrl}
                alt={`${currentScreenLabel} 预览`}
                className="screen-preview-image is-visible"
              />
            ) : isPreviewing ? (
              <video ref={previewRef} className={isPreviewing ? "screen-preview is-visible" : "screen-preview"} />
            ) : (
              <div className="screen-preview-empty">未获取到屏幕预览</div>
            )}
            {isPreviewing ? <button type="button" className="secondary-button compact" onClick={stopPreview}>关闭预览</button> : null}
          </section>

          <section className="connection-card" aria-label="连接管理">
            <div className="connection-head">
              <div>
                <h2>连接管理</h2>
                <p>管理设备连接和状态</p>
              </div>
              <button type="button" className="code-box" onClick={() => { void copyConnectionCode(); }} aria-label="复制连接码">
                <span>连接码：</span>
                <strong>{pairingIdentity?.manualCode ?? "------"}</strong>
              </button>
            </div>

            <div className="connection-status">
              {desktopNotice ? <p className="desktop-notice">{desktopNotice}</p> : null}
              <p>
                <strong>连接状态：</strong>
                <span className={activeBinding ? "status-light green" : "status-light red"} />
                {activeBinding ? (
                  <span>已连接 | 网页端已绑定本机</span>
                ) : (
                  <span>{connectionNotice || "未连接"}</span>
                )}
              </p>
              <p>
                <strong>连接信息：</strong>
                <span className="muted-chip">{connectionInfo}</span>
                {!activeBinding ? (
                  <button type="button" className="inline-web-link" onClick={() => { void openResolvedUrl("home"); }}>
                    打开面试首页
                  </button>
                ) : null}
                <button type="button" className="inline-web-link" onClick={() => { void resetAuthorization(); }}>
                  重新授权
                </button>
                {activeBinding ? null : (
                  <button type="button" className="inline-web-link" onClick={() => { void window.offersteady?.openPermissionSettings("microphone"); }}>
                    打开麦克风权限设置
                  </button>
                ) : null}
              </p>
              <p className="route-copy">
                当前路由：我的声音来自麦克风/耳机；面试官声音来自电脑输出音频，也就是微信、会议或网页面试在这台电脑上播放出来的声音；屏幕捕捉用于截图回答。
              </p>
              {webOpenNotice ? <p className="route-copy">{webOpenNotice}</p> : null}
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
