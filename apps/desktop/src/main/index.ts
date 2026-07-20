import { app, BrowserWindow, Menu, Tray, desktopCapturer, ipcMain, nativeImage, safeStorage, session, shell, systemPreferences } from "electron";
import { execFile, spawn, type ChildProcess } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";
import type { CaptureState } from "@offersteady/protocol" with { "resolution-mode": "import" };
import { DeviceCredentialVault } from "./credential-vault";
import { DevicePairingIdentityStore } from "./device-pairing";

let mainWindow: BrowserWindow | null = null;
let tray: Tray | null = null;
let captureState: CaptureState = "not-connected";
let isQuitting = false;
let credentialVault: DeviceCredentialVault | null = null;
let pairingIdentityStore: DevicePairingIdentityStore | null = null;
let registrationInterval: NodeJS.Timeout | null = null;
let screenshotRequestInterval: NodeJS.Timeout | null = null;
let realtimeAudioInterval: NodeJS.Timeout | null = null;
let preferredScreenSourceId: string | null = null;
let hasRegisteredThisRun = false;
let processingRemoteScreenshotRequestId: string | null = null;
const nativeAudioProcesses = new Map<string, ChildProcess>();
let mainRealtimeBindingKey: string | null = null;
let mainRealtimeBinding: {
  sessionId: string;
  ownerUserId: string;
  deviceId: string;
  manualCode: string;
  displayName?: string;
} | null = null;
let mainRealtimePublisherTokens = new Map<"microphone" | "system", { token: string; sourceId: string }>();
let mainRealtimePublisherPromises = new Map<"microphone" | "system", Promise<{ token: string; sourceId: string } | null>>();
let mainRealtimeSequences = new Map<"microphone" | "system", number>();
let mainRealtimeEnsureInFlight = false;
let mainRealtimeOwnsNativeAudio = false;
let rendererOwnsNativeAudio = false;
let desktopRegistrationInFlight = false;
let remoteScreenshotPollInFlight = false;
const activeDesktopRequestControllers = new Set<AbortController>();
const desktopApiRequestsInFlight = new Map<string, Promise<DesktopApiRequestResult>>();
const SCREENSHOT_VISION_MAX_LONG_EDGE = 1600;
const SCREENSHOT_VISION_JPEG_QUALITY = 72;
const DESKTOP_CONTROL_REQUEST_TIMEOUT_MS = 8_000;
const DESKTOP_AUDIO_REQUEST_TIMEOUT_MS = 12_000;
const DESKTOP_UPLOAD_REQUEST_TIMEOUT_MS = 30_000;

interface DesktopApiRequestResult {
  readonly ok: boolean;
  readonly status: number;
  readonly statusText: string;
  readonly headers: Record<string, string>;
  readonly bodyText: string;
}

const fetchWithTimeout = async (
  input: string | URL,
  init: RequestInit = {},
  timeoutMs = DESKTOP_CONTROL_REQUEST_TIMEOUT_MS,
) => {
  const controller = new AbortController();
  const callerSignal = init.signal;
  const abortFromCaller = () => controller.abort(callerSignal?.reason);
  if (callerSignal?.aborted) abortFromCaller();
  else callerSignal?.addEventListener("abort", abortFromCaller, { once: true });
  activeDesktopRequestControllers.add(controller);
  const timeout = setTimeout(() => controller.abort(new Error("desktop_request_timeout")), timeoutMs);
  try {
    return await fetch(input, { ...init, signal: controller.signal });
  } finally {
    clearTimeout(timeout);
    callerSignal?.removeEventListener("abort", abortFromCaller);
    activeDesktopRequestControllers.delete(controller);
  }
};

const abortPendingDesktopRequests = () => {
  for (const controller of activeDesktopRequestControllers) controller.abort(new Error("desktop_app_quitting"));
  activeDesktopRequestControllers.clear();
  desktopApiRequestsInFlight.clear();
};

const emitNativeAudioEvent = (event: Record<string, unknown>) => {
  mainWindow?.webContents.send("desktop:native-audio-event", event);
};

const stopNativeAudioStreams = () => {
  for (const child of nativeAudioProcesses.values()) {
    child.kill("SIGTERM");
  }
  nativeAudioProcesses.clear();
};

const stateLabels: Record<CaptureState, string> = {
  "not-connected": "未连接",
  "permission-required": "需要权限",
  ready: "收音已就绪",
  capturing: "正在收音",
  paused: "已暂停",
  reconnecting: "正在重连",
  error: "连接异常",
};

const defaultWebWorkspaceUrl = () => "https://mianshiwen.cn/app";
const defaultApiBaseUrl = () => "https://mianshiwen.cn/api/v1";

const desktopConfig = () => ({
  appVersion: app.getVersion(),
  platform: process.platform === "darwin" ? "macos" : process.platform === "win32" ? "windows" : "unsupported",
  architecture: process.arch === "arm64" ? "arm64" : process.arch === "x64" ? "x64" : "unknown",
  platformVersion: process.getSystemVersion(),
  protocolVersion: "1.0.0",
  webWorkspaceUrl: process.env.OFFERSTEADY_DESKTOP_WEB_URL || defaultWebWorkspaceUrl(),
  apiBaseUrl: process.env.OFFERSTEADY_API_BASE_URL || defaultApiBaseUrl(),
});

const nativeRuntimePath = () => {
  const packagedPath = path.join(process.resourcesPath, "app/native/macos-capture/OfferSteadyCaptureRuntime");
  if (existsSync(packagedPath)) return packagedPath;
  return path.resolve(__dirname, "../native/macos-capture/OfferSteadyCaptureRuntime");
};

const getNativeRuntimeHealth = async () => {
  if (process.platform !== "darwin") {
    return { available: false, ready: false, errorCode: "unsupported-platform", message: "当前 native capture runtime 仅支持 macOS。" };
  }
  const helper = nativeRuntimePath();
  if (!existsSync(helper)) {
    return { available: false, ready: false, errorCode: "native-runtime-missing", message: "缺少 macOS 原生采集运行时，请重新打包安装伴随程序。" };
  }
  return new Promise((resolve) => {
    execFile(helper, [], { timeout: 5000 }, (error, stdout, stderr) => {
      if (error) {
        resolve({ available: true, ready: false, errorCode: "native-runtime-health-failed", message: stderr || error.message });
        return;
      }
      try {
        resolve({ available: true, ...JSON.parse(stdout.trim()) });
      } catch {
        resolve({ available: true, ready: false, errorCode: "native-runtime-invalid-output", message: stdout.trim() || "原生采集运行时没有返回有效健康状态。" });
      }
    });
  });
};

const optimizeScreenshotForVision = (image: Electron.NativeImage) => {
  const size = image.getSize();
  const longest = Math.max(size.width, size.height);
  const ratio = longest > SCREENSHOT_VISION_MAX_LONG_EDGE ? SCREENSHOT_VISION_MAX_LONG_EDGE / longest : 1;
  const optimized = ratio < 1
    ? image.resize({
      width: Math.max(1, Math.round(size.width * ratio)),
      height: Math.max(1, Math.round(size.height * ratio)),
      quality: "best",
    })
    : image;
  const optimizedSize = optimized.getSize();
  const jpeg = optimized.toJPEG(SCREENSHOT_VISION_JPEG_QUALITY);
  return {
    dataUrl: `data:image/jpeg;base64,${jpeg.toString("base64")}`,
    width: optimizedSize.width,
    height: optimizedSize.height,
    byteLength: jpeg.length,
    contentType: "image/jpeg",
    extension: "jpg",
  };
};

const startNativeAudioProcess = (sourceKind: "microphone" | "system", sourceId: string) => {
  if (process.platform !== "darwin") {
    emitNativeAudioEvent({
      type: "status",
      sourceKind,
      sourceId,
      errorCode: "unsupported-platform",
      message: "当前原生实时采集仅支持 macOS。",
    });
    return false;
  }
  const helper = nativeRuntimePath();
  if (!existsSync(helper)) {
    emitNativeAudioEvent({
      type: "status",
      sourceKind,
      sourceId,
      errorCode: "native-runtime-missing",
      message: "缺少 macOS 原生采集运行时，请重新打包安装伴随程序。",
    });
    return false;
  }
  const command = sourceKind === "microphone" ? "stream-microphone" : "stream-system";
  const child = spawn(helper, [command, sourceId], { stdio: ["ignore", "pipe", "pipe"] });
  nativeAudioProcesses.set(sourceKind, child);
  let stdoutBuffer = "";
  child.stdout.setEncoding("utf8");
  child.stdout.on("data", (chunk) => {
    stdoutBuffer += chunk;
    let newlineIndex = stdoutBuffer.indexOf("\n");
    while (newlineIndex >= 0) {
      const line = stdoutBuffer.slice(0, newlineIndex).trim();
      stdoutBuffer = stdoutBuffer.slice(newlineIndex + 1);
      if (line) {
        try {
          const event = JSON.parse(line);
          emitNativeAudioEvent(event);
          void publishNativeAudioEventFromMain(event).catch((error) => {
            console.warn("[main-realtime-audio] frame publish failed", error);
          });
        } catch {
          emitNativeAudioEvent({
            type: "status",
            sourceKind,
            sourceId,
            errorCode: "native-runtime-invalid-event",
            message: "原生采集运行时返回了无法解析的事件。",
          });
        }
      }
      newlineIndex = stdoutBuffer.indexOf("\n");
    }
  });
  child.stderr.setEncoding("utf8");
  child.stderr.on("data", (chunk) => {
    const message = String(chunk).trim();
    if (!message) return;
    emitNativeAudioEvent({
      type: "status",
      sourceKind,
      sourceId,
      errorCode: "native-runtime-stderr",
      message,
    });
  });
  child.on("exit", (code, signal) => {
    if (nativeAudioProcesses.get(sourceKind) === child) nativeAudioProcesses.delete(sourceKind);
    if (signal === "SIGTERM") return;
    emitNativeAudioEvent({
      type: "status",
      sourceKind,
      sourceId,
      errorCode: code === 0 ? null : "native-runtime-exited",
      message: code === 0 ? "原生采集流已结束。" : `原生采集流异常退出：${code ?? "unknown"}`,
    });
  });
  child.on("error", (error) => {
    if (nativeAudioProcesses.get(sourceKind) === child) nativeAudioProcesses.delete(sourceKind);
    emitNativeAudioEvent({
      type: "status",
      sourceKind,
      sourceId,
      errorCode: "native-runtime-spawn-failed",
      message: error.message,
    });
  });
  return true;
};

const createMainRealtimePublisher = async (
  binding: { sessionId: string; ownerUserId: string; displayName?: string },
  sourceKind: "microphone" | "system",
) => {
  const response = await fetchWithTimeout(desktopApiUrl("/realtime-speech/publishers"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      userId: binding.ownerUserId,
      sessionId: binding.sessionId,
      sourceKind,
      clientName: `${binding.displayName || app.getName()} · main-${sourceKind}`,
    }),
  });
  if (!response.ok) throw new Error(`main_publisher_create_failed_${sourceKind}_${response.status}`);
  const envelope = await response.json() as { data?: { token?: string } };
  const token = envelope.data?.token;
  if (!token) throw new Error(`main_publisher_token_missing_${sourceKind}`);
  return token;
};

const stopMainRealtimeAudioPublishing = () => {
  if (mainRealtimeOwnsNativeAudio) stopNativeAudioStreams();
  mainRealtimeOwnsNativeAudio = false;
  mainRealtimeBindingKey = null;
  mainRealtimeBinding = null;
  mainRealtimePublisherTokens.clear();
  mainRealtimePublisherPromises.clear();
  mainRealtimeSequences.clear();
  mainRealtimeEnsureInFlight = false;
};

const ensureMainRealtimePublisher = async (sourceKind: "microphone" | "system", sourceId: string) => {
  const existing = mainRealtimePublisherTokens.get(sourceKind);
  if (existing) return existing;
  if (!mainRealtimeBinding || rendererOwnsNativeAudio) return null;
  const pending = mainRealtimePublisherPromises.get(sourceKind);
  if (pending) return pending;
  const promise = createMainRealtimePublisher(mainRealtimeBinding, sourceKind)
    .then((token) => {
      const tokenInfo = { token, sourceId };
      mainRealtimePublisherTokens.set(sourceKind, tokenInfo);
      return tokenInfo;
    })
    .catch((error) => {
      console.warn(`[main-realtime-audio] ${sourceKind} publisher failed`, error);
      return null;
    })
    .finally(() => {
      mainRealtimePublisherPromises.delete(sourceKind);
    });
  mainRealtimePublisherPromises.set(sourceKind, promise);
  return promise;
};

const getLiveDesktopBinding = async () => {
  if (!pairingIdentityStore) return null;
  const identity = await pairingIdentityStore.loadOrCreate(`${app.getName()} · ${process.platform === "darwin" ? "Mac" : "Desktop"}`);
  const response = await fetchWithTimeout(desktopApiUrl(`/realtime-speech/desktop-devices/pairing-status?manualCode=${encodeURIComponent(identity.manualCode)}&deviceId=${encodeURIComponent(identity.deviceId)}`));
  if (!response.ok) return null;
  const envelope = await response.json() as {
    data?: {
      registered?: boolean;
      bound?: boolean;
      sessionStatus?: string;
      binding?: {
        sessionId: string;
        ownerUserId: string;
        deviceId: string;
        manualCode: string;
        displayName?: string;
      };
    };
  };
  if (!envelope.data?.registered || envelope.data.sessionStatus !== "live" || !envelope.data.binding) return null;
  return envelope.data.binding;
};

const ensureMainRealtimeAudioPublishing = async () => {
  if (mainRealtimeEnsureInFlight) return;
  mainRealtimeEnsureInFlight = true;
  try {
    if (rendererOwnsNativeAudio) {
      if (mainRealtimeBindingKey || mainRealtimePublisherTokens.size > 0) stopMainRealtimeAudioPublishing();
      return;
    }
    const binding = await getLiveDesktopBinding();
    if (!binding) {
      if (mainRealtimeBindingKey) stopMainRealtimeAudioPublishing();
      return;
    }
    const bindingKey = `${binding.sessionId}:${binding.ownerUserId}:${binding.deviceId}:${binding.manualCode}`;
    if (mainRealtimeBindingKey !== bindingKey) {
      stopMainRealtimeAudioPublishing();
      mainRealtimeEnsureInFlight = true;
      mainRealtimeBindingKey = bindingKey;
      mainRealtimeBinding = binding;
    }
    const microphoneStarted = nativeAudioProcesses.has("microphone")
      || startNativeAudioProcess("microphone", "native-microphone");
    const systemStarted = nativeAudioProcesses.has("system")
      || startNativeAudioProcess("system", "native-system-output");
    mainRealtimeOwnsNativeAudio = microphoneStarted || systemStarted;
  } finally {
    mainRealtimeEnsureInFlight = false;
  }
};

const publishNativeAudioEventFromMain = async (event: Record<string, unknown>) => {
  if (event.type !== "frame") return;
  if (event.sourceKind !== "microphone" && event.sourceKind !== "system") return;
  if (rendererOwnsNativeAudio) return;
  const sourceKind = event.sourceKind;
  if (typeof event.audioBase64 !== "string" || !event.audioBase64) return;
  const eventSourceId = typeof event.sourceId === "string"
    ? event.sourceId
    : sourceKind === "microphone" ? "native-microphone" : "native-system-output";
  const tokenInfo = await ensureMainRealtimePublisher(sourceKind, eventSourceId);
  if (!tokenInfo) return;
  const sequence = (mainRealtimeSequences.get(sourceKind) ?? 0) + 1;
  mainRealtimeSequences.set(sourceKind, sequence);
  const capturedAtMs = typeof event.capturedAtMs === "number" ? event.capturedAtMs : Date.now();
  const durationMs = typeof event.durationMs === "number" ? event.durationMs : 20;
  const sampleRateHz = typeof event.sampleRateHz === "number" ? event.sampleRateHz : 16_000;
  const channels = event.channels === 2 ? 2 : 1;
  const response = await fetchWithTimeout(desktopApiUrl("/realtime-speech/frames"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      type: "audio-frame",
      token: tokenInfo.token,
      deviceId: (await pairingIdentityStore?.loadOrCreate(`${app.getName()} · ${process.platform === "darwin" ? "Mac" : "Desktop"}`))?.deviceId || "",
      sourceId: typeof event.sourceId === "string" ? event.sourceId : tokenInfo.sourceId,
      sourceKind,
      sequence,
      segmentId: `${sourceKind}-main-${sequence}`,
      revision: 1,
      capturedAtMs,
      startedAtMs: capturedAtMs - durationMs,
      endedAtMs: capturedAtMs,
      durationMs,
      codec: "pcm-s16le",
      sampleRateHz,
      channels,
      isFinal: true,
      traceId: `${sourceKind}:main:${sequence}`,
      sentAtMs: Date.now(),
      audioBase64: event.audioBase64,
    }),
  }, DESKTOP_AUDIO_REQUEST_TIMEOUT_MS);
  if (!response.ok) {
    const message = await response.text().catch(() => "");
    throw new Error(`main_frame_publish_failed_${response.status}:${message.slice(0, 200)}`);
  }
};

const startMainRealtimeAudioLoop = () => {
  // Protocol v2 has one renderer transport fed by the native Swift runtime.
  // Keep the legacy main-process HTTP publisher stopped to avoid duplicates.
  if (realtimeAudioInterval) clearInterval(realtimeAudioInterval);
  realtimeAudioInterval = null;
  if (process.env.OFFERSTEADY_ENABLE_LEGACY_MAIN_AUDIO !== "1") return;
  void ensureMainRealtimeAudioPublishing().catch((error) => console.warn("[main-realtime-audio] ensure failed", error));
  realtimeAudioInterval = setInterval(() => {
    void ensureMainRealtimeAudioPublishing().catch((error) => console.warn("[main-realtime-audio] ensure failed", error));
  }, 2500);
};

const probeWebUrl = async (url: string) => {
  try {
    const response = await fetchWithTimeout(url, { method: "GET", redirect: "manual" }, 5_000);
    return response.status >= 200 && response.status < 500;
  } catch {
    return false;
  }
};

const apiBaseParts = () => {
  const base = new URL(desktopConfig().apiBaseUrl);
  return {
    origin: base.origin,
    pathname: base.pathname.replace(/\/+$/, ""),
  };
};

const assertOfferSteadyApiUrl = (url: string) => {
  const base = apiBaseParts();
  const requested = new URL(url, desktopConfig().apiBaseUrl);
  const normalizedPath = requested.pathname.replace(/\/+$/, "");
  if (requested.origin !== base.origin || (base.pathname && !normalizedPath.startsWith(base.pathname))) {
    throw new Error("desktop_api_url_not_allowed");
  }
  return requested.toString();
};

const desktopCapabilities = () => {
  const config = desktopConfig();
  return {
    protocolVersion: config.protocolVersion,
    appVersion: config.appVersion,
    platform: config.platform,
    architecture: config.architecture,
    platformVersion: config.platformVersion,
    microphone: "unknown",
    systemAudio: "unknown",
    availableSources: [],
    screenCapture: true,
  };
};

const syncDesktopRegistration = async () => {
  if (!pairingIdentityStore) return false;
  const identity = await pairingIdentityStore.loadOrCreate(`${app.getName()} · ${process.platform === "darwin" ? "Mac" : "Desktop"}`);
  const config = desktopConfig();
  try {
    const endpoint = hasRegisteredThisRun
      ? `${config.apiBaseUrl}/realtime-speech/desktop-devices/${encodeURIComponent(identity.deviceId)}/heartbeat`
      : `${config.apiBaseUrl}/realtime-speech/desktop-devices/register`;
    const response = await fetchWithTimeout(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...(hasRegisteredThisRun ? {} : { deviceId: identity.deviceId }),
        manualCode: identity.manualCode,
        displayName: identity.displayName,
        capabilities: desktopCapabilities(),
      }),
    });
    if (!response.ok) {
      if (hasRegisteredThisRun && response.status === 404) hasRegisteredThisRun = false;
      console.warn(`[desktop-registration] failed with status ${response.status}`);
      return false;
    }
    hasRegisteredThisRun = true;
    return true;
  } catch (error) {
    console.warn("[desktop-registration] request failed", error);
    return false;
  }
};

const startDesktopRegistrationLoop = () => {
  if (registrationInterval) clearInterval(registrationInterval);
  const run = async () => {
    if (desktopRegistrationInFlight) return;
    desktopRegistrationInFlight = true;
    try {
      await syncDesktopRegistration();
    } finally {
      desktopRegistrationInFlight = false;
    }
  };
  void run();
  registrationInterval = setInterval(() => {
    void run();
  }, 10000);
};

const desktopApiUrl = (pathName: string) => {
  const config = desktopConfig();
  return `${config.apiBaseUrl.replace(/\/+$/, "")}/${pathName.replace(/^\/+/, "")}`;
};

const allowedRuntimePermissions = new Set(["media", "display-capture"]);

const permissionSettingsUrl = (kind: "microphone" | "screen" | "camera" | "audio") => {
  if (kind === "microphone" || kind === "audio") return "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone";
  if (kind === "camera") return "x-apple.systempreferences:com.apple.preference.security?Privacy_Camera";
  return "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture";
};

const trayImage = () => {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32"><rect width="32" height="32" rx="8" fill="#5ee0b5"/><text x="16" y="22" text-anchor="middle" font-size="18" font-family="sans-serif" font-weight="700" fill="#07130f">稳</text></svg>`;
  return nativeImage.createFromDataURL(`data:image/svg+xml;base64,${Buffer.from(svg).toString("base64")}`);
};

const updateTray = () => {
  if (!tray) return;
  tray.setToolTip(`面试稳伴随程序 · ${stateLabels[captureState]}`);
  tray.setContextMenu(Menu.buildFromTemplate([
    { label: stateLabels[captureState], enabled: false },
    { type: "separator" },
    { label: "打开伴随程序", click: () => mainWindow?.show() },
    {
      label: "停止并退出",
      click: () => {
        captureState = "not-connected";
        app.quit();
      },
    },
  ]));
};

const captureCurrentScreen = async (screenSourceId: string | null) => {
  let sources;
  try {
    sources = await desktopCapturer.getSources({
      types: ["screen"],
      thumbnailSize: { width: 1920, height: 1080 },
    });
  } catch (error) {
    return {
      name: "共享屏幕截取",
      errorMessage: error instanceof Error
        ? `获取屏幕源失败：${error.message}。请在系统设置中允许面试稳伴随程序录制屏幕后重启应用。`
        : "获取屏幕源失败，请在系统设置中允许面试稳伴随程序录制屏幕后重启应用。",
    };
  }
  const requestedScreenSourceId = screenSourceId || preferredScreenSourceId;
  const selectedScreen = requestedScreenSourceId
    ? sources.find((source) => source.id === requestedScreenSourceId)
    : sources[0];
  if (requestedScreenSourceId && !selectedScreen) {
    return {
      name: "共享屏幕截取",
      errorMessage: "当前选择的屏幕源已经不可用，请在本地助手中重新选择显示器后再试。",
    };
  }
  if (!selectedScreen) {
    return { name: "共享屏幕截取", errorMessage: "没有找到可截取的屏幕，请检查屏幕录制权限。" };
  }
  const thumbnail = selectedScreen.thumbnail;
  const size = thumbnail.getSize();
  if (thumbnail.isEmpty()) {
    return {
      name: selectedScreen.name || "共享屏幕截取",
      width: size.width,
      height: size.height,
      errorMessage: "屏幕缩略图为空，请在系统设置中允许面试稳伴随程序录制屏幕后重启应用。",
    };
  }
  const optimized = optimizeScreenshotForVision(thumbnail);
  return {
    name: selectedScreen.name || "共享屏幕截取",
    width: optimized.width,
    height: optimized.height,
    dataUrl: optimized.dataUrl,
    contentType: optimized.contentType,
    byteLength: optimized.byteLength,
    originalWidth: size.width,
    originalHeight: size.height,
    extension: optimized.extension,
  };
};

const uploadScreenshotCapture = async (request: {
  url: string;
  deviceId: string;
  manualCode: string;
  dataUrl: string;
  filename: string;
}) => {
  const url = assertOfferSteadyApiUrl(request.url);
  const [meta, payload] = request.dataUrl.split(",", 2);
  if (!meta || !payload) throw new Error("invalid_screenshot_data_url");
  const mimeType = meta.match(/^data:(.*?);base64$/)?.[1] || "image/png";
  const binary = Buffer.from(payload, "base64");
  const form = new FormData();
  form.append("deviceId", request.deviceId);
  form.append("manualCode", request.manualCode);
  form.append("screenshot", new Blob([binary], { type: mimeType }), request.filename);
  const response = await fetchWithTimeout(url, {
    method: "POST",
    body: form,
  }, DESKTOP_UPLOAD_REQUEST_TIMEOUT_MS);
  return {
    ok: response.ok,
    status: response.status,
    statusText: response.statusText,
    headers: Object.fromEntries(response.headers.entries()),
    bodyText: await response.text(),
  };
};

const reportRemoteScreenshotFailure = async (identity: { deviceId: string; manualCode: string }, requestId: string, message: string, stage = "capture-failed") => {
  try {
    await fetchWithTimeout(desktopApiUrl(`/screenshot-answer/capture-requests/${encodeURIComponent(requestId)}/desktop-fail`), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        deviceId: identity.deviceId,
        manualCode: identity.manualCode,
        message,
        stage,
      }),
    });
  } catch (error) {
    console.warn("[remote-screenshot] failed to report capture failure", error);
  }
};

const pollRemoteScreenshotRequest = async () => {
  if (!pairingIdentityStore || processingRemoteScreenshotRequestId) return;
  const identity = await pairingIdentityStore.loadOrCreate(`${app.getName()} · ${process.platform === "darwin" ? "Mac" : "Desktop"}`);
  const response = await fetchWithTimeout(desktopApiUrl(`/screenshot-answer/desktop-devices/${encodeURIComponent(identity.deviceId)}/capture-requests/next?manualCode=${encodeURIComponent(identity.manualCode)}`));
  if (!response.ok) return;
  const envelope = await response.json() as { data?: { requestId: string; status: string } | null };
  const request = envelope.data;
  if (!request || request.status === "completed" || request.status === "failed") return;
  processingRemoteScreenshotRequestId = request.requestId;
  try {
    mainWindow?.webContents.send("desktop:remote-screenshot-notice", "网页端已请求截图回答，本地助手正在截取当前屏幕。");
    const capture = await captureCurrentScreen(null);
    if (capture.errorMessage) throw new Error(capture.errorMessage);
    if (!capture.dataUrl) throw new Error("本地助手未获取到有效共享屏幕画面，请检查屏幕捕捉权限。");
    const extension = capture.extension || (capture.contentType === "image/jpeg" ? "jpg" : capture.contentType === "image/webp" ? "webp" : "png");
    const filename = `${(capture.name || "current-screen").replace(/[\\/:*?"<>|]+/g, "-")}.${extension}`;
    const upload = await uploadScreenshotCapture({
      url: desktopApiUrl(`/screenshot-answer/capture-requests/${encodeURIComponent(request.requestId)}/desktop-upload`),
      deviceId: identity.deviceId,
      manualCode: identity.manualCode,
      dataUrl: capture.dataUrl,
      filename,
    });
    if (!upload.ok) throw new Error(upload.bodyText || `截图上传失败：${upload.status}`);
    mainWindow?.webContents.send("desktop:remote-screenshot-notice", "本地助手已完成截图并回传后端。");
  } catch (error) {
    const message = error instanceof Error ? error.message : "本地助手执行截图回答失败";
    await reportRemoteScreenshotFailure(identity, request.requestId, message, message.includes("上传") ? "upload-failed" : "capture-failed");
    mainWindow?.webContents.send("desktop:remote-screenshot-notice", `截图失败：${message}`);
  } finally {
    processingRemoteScreenshotRequestId = null;
  }
};

const startRemoteScreenshotRequestLoop = () => {
  if (screenshotRequestInterval) clearInterval(screenshotRequestInterval);
  const run = async () => {
    if (remoteScreenshotPollInFlight) return;
    remoteScreenshotPollInFlight = true;
    try {
      await pollRemoteScreenshotRequest();
    } catch (error) {
      console.warn("[remote-screenshot] poll failed", error);
    } finally {
      remoteScreenshotPollInFlight = false;
    }
  };
  void run();
  screenshotRequestInterval = setInterval(() => {
    void run();
  }, 1200);
};

const createWindow = () => {
  mainWindow = new BrowserWindow({
    width: 780,
    height: 760,
    minWidth: 700,
    minHeight: 680,
    title: "面试稳伴随程序",
    backgroundColor: "#080d18",
    show: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  mainWindow.removeMenu();
  void mainWindow.loadFile(path.join(__dirname, "../renderer/index.html"));
  mainWindow.once("ready-to-show", () => mainWindow?.show());
  mainWindow.on("close", (event) => {
    if (!isQuitting) {
      event.preventDefault();
      mainWindow?.hide();
    }
  });
};

app.whenReady().then(() => {
  captureState = "not-connected";
  credentialVault = new DeviceCredentialVault(app.getPath("userData"), safeStorage);
  pairingIdentityStore = new DevicePairingIdentityStore(app.getPath("userData"));
  session.defaultSession.setPermissionRequestHandler((_webContents, permission, callback) => {
    callback(allowedRuntimePermissions.has(permission));
  });
  session.defaultSession.setPermissionCheckHandler((_webContents, permission) => allowedRuntimePermissions.has(permission));
  session.defaultSession.setDisplayMediaRequestHandler((request, callback) => {
    void desktopCapturer.getSources({
        types: ["screen"],
        thumbnailSize: { width: 0, height: 0 },
      })
      .then((sources) => {
      const selectedScreen = (preferredScreenSourceId
        ? sources.find((source) => source.id === preferredScreenSourceId)
        : null) ?? sources[0];
      if (!selectedScreen) {
        try {
          callback({});
        } catch (error) {
          console.warn("[desktop-capture] display media callback rejected an empty source", error);
        }
        return;
      }
      callback({
        ...(request.videoRequested ? { video: selectedScreen } : {}),
        ...(request.audioRequested ? { audio: "loopback" } : {}),
      });
      })
      .catch((error) => {
        console.warn("[desktop-capture] display media source unavailable", error);
        try {
          callback({});
        } catch (callbackError) {
          console.warn("[desktop-capture] display media callback rejected an unavailable source", callbackError);
        }
      });
  }, { useSystemPicker: false });
  tray = new Tray(trayImage());
  updateTray();
  createWindow();
  startDesktopRegistrationLoop();
  startRemoteScreenshotRequestLoop();

  app.on("activate", () => mainWindow?.show());
});

ipcMain.on("capture:set-state", (_event, state: CaptureState) => {
  captureState = state;
  updateTray();
});

ipcMain.on("app:close", () => {
  captureState = "not-connected";
  stopNativeAudioStreams();
  app.quit();
});

ipcMain.handle("credential:save", async (_event, credential: string) => {
  await credentialVault?.save(credential);
});

ipcMain.handle("credential:clear", async () => {
  await credentialVault?.clear();
});

ipcMain.handle("desktop:get-config", async () => desktopConfig());
ipcMain.handle("desktop:get-native-runtime-health", async () => getNativeRuntimeHealth());
ipcMain.handle("desktop:start-native-audio-stream", async (_event, options: { microphoneSourceId?: string; systemSourceId?: string }) => {
  stopMainRealtimeAudioPublishing();
  stopNativeAudioStreams();
  rendererOwnsNativeAudio = true;
  const microphoneStarted = startNativeAudioProcess("microphone", options.microphoneSourceId || "native-microphone");
  const systemStarted = startNativeAudioProcess("system", options.systemSourceId || "native-system-output");
  if (!microphoneStarted && !systemStarted) rendererOwnsNativeAudio = false;
  return { ok: microphoneStarted || systemStarted, microphoneStarted, systemStarted };
});
ipcMain.handle("desktop:stop-native-audio-stream", async () => {
  rendererOwnsNativeAudio = false;
  stopNativeAudioStreams();
  return { ok: true };
});

ipcMain.handle("desktop:get-pairing-identity", async () => {
  if (!pairingIdentityStore) pairingIdentityStore = new DevicePairingIdentityStore(app.getPath("userData"));
  return pairingIdentityStore.loadOrCreate(`${app.getName()} · ${process.platform === "darwin" ? "Mac" : "Desktop"}`);
});

ipcMain.handle("desktop:reset-pairing-identity", async () => {
  if (!pairingIdentityStore) pairingIdentityStore = new DevicePairingIdentityStore(app.getPath("userData"));
  await pairingIdentityStore.reset();
  hasRegisteredThisRun = false;
  return true;
});

ipcMain.handle("desktop:list-screens", async () => {
  try {
    const sources = await desktopCapturer.getSources({
      types: ["screen"],
      thumbnailSize: { width: 1280, height: 720 },
    });
    return sources.map((source, index) => ({
      id: source.id,
      label: source.name || `显示器 ${index + 1}`,
      thumbnailDataUrl: source.thumbnail.isEmpty() ? null : source.thumbnail.toDataURL(),
    }));
  } catch {
    return [];
  }
});

ipcMain.handle("desktop:set-preferred-screen", async (_event, screenSourceId: string | null) => {
  preferredScreenSourceId = screenSourceId;
  return { ok: true };
});

ipcMain.handle("desktop:capture-current-screen", async (_event, screenSourceId: string | null) => {
  return captureCurrentScreen(screenSourceId);
});

ipcMain.handle("desktop:upload-screenshot-capture", async (_event, request: {
  url: string;
  deviceId: string;
  manualCode: string;
  dataUrl: string;
  filename: string;
}) => {
  return uploadScreenshotCapture(request);
});

ipcMain.handle("desktop:open-external", async (_event, url: string) => {
  await shell.openExternal(url);
});

ipcMain.handle("desktop:probe-web-url", async (_event, url: string) => probeWebUrl(url));

ipcMain.handle("desktop:api-request", async (_event, request: { url: string; method?: string; headers?: Record<string, string>; body?: string | null }) => {
  const url = assertOfferSteadyApiUrl(request.url);
  const method = (request.method ?? "GET").toUpperCase();
  const isAudioFrame = new URL(url).pathname.endsWith("/realtime-speech/frames");
  const canCoalesce = !isAudioFrame && (method === "GET"
    || url.includes("/desktop-devices/register")
    || url.includes("/desktop-devices/") && url.includes("/heartbeat")
    || url.includes("/device-status"));
  const requestKey = canCoalesce ? `${method}:${url}:${request.body ?? ""}` : null;
  if (requestKey) {
    const pending = desktopApiRequestsInFlight.get(requestKey);
    if (pending) return pending;
  }
  const execute = async (): Promise<DesktopApiRequestResult> => {
    const response = await fetchWithTimeout(url, {
      method,
      headers: request.headers,
      body: request.body ?? undefined,
    }, isAudioFrame ? DESKTOP_AUDIO_REQUEST_TIMEOUT_MS : DESKTOP_CONTROL_REQUEST_TIMEOUT_MS);
    return {
      ok: response.ok,
      status: response.status,
      statusText: response.statusText,
      headers: Object.fromEntries(response.headers.entries()),
      bodyText: await response.text(),
    };
  };
  const promise = execute();
  if (!requestKey) return promise;
  desktopApiRequestsInFlight.set(requestKey, promise);
  try {
    return await promise;
  } finally {
    if (desktopApiRequestsInFlight.get(requestKey) === promise) desktopApiRequestsInFlight.delete(requestKey);
  }
});

ipcMain.handle("desktop:request-microphone-access", async () => {
  if (process.platform !== "darwin") return true;
  return systemPreferences.askForMediaAccess("microphone");
});

ipcMain.handle("desktop:open-permission-settings", async (_event, kind: "microphone" | "screen" | "camera" | "audio") => {
  await shell.openExternal(permissionSettingsUrl(kind));
});

app.on("window-all-closed", () => {
  // The tray remains the persistent, visible control surface.
});

app.on("before-quit", () => {
  isQuitting = true;
  captureState = "not-connected";
  if (registrationInterval) {
    clearInterval(registrationInterval);
    registrationInterval = null;
  }
  if (screenshotRequestInterval) {
    clearInterval(screenshotRequestInterval);
    screenshotRequestInterval = null;
  }
  if (realtimeAudioInterval) {
    clearInterval(realtimeAudioInterval);
    realtimeAudioInterval = null;
  }
  abortPendingDesktopRequests();
  stopMainRealtimeAudioPublishing();
});
