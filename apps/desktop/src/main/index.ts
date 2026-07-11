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
let preferredScreenSourceId: string | null = null;
let hasRegisteredThisRun = false;
const nativeAudioProcesses = new Map<string, ChildProcess>();
const SCREENSHOT_VISION_MAX_LONG_EDGE = 1600;
const SCREENSHOT_VISION_JPEG_QUALITY = 72;

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
          emitNativeAudioEvent(JSON.parse(line));
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

const probeWebUrl = async (url: string) => {
  try {
    const response = await fetch(url, { method: "GET", redirect: "manual" });
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
    const response = await fetch(endpoint, {
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
  void syncDesktopRegistration();
  registrationInterval = setInterval(() => {
    void syncDesktopRegistration();
  }, 10000);
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
  session.defaultSession.setDisplayMediaRequestHandler(async (request, callback) => {
    const sources = await desktopCapturer.getSources({
      types: ["screen"],
      thumbnailSize: { width: 0, height: 0 },
    });
    const selectedScreen = (preferredScreenSourceId
      ? sources.find((source) => source.id === preferredScreenSourceId)
      : null) ?? sources[0];
    if (!selectedScreen) {
      callback({});
      return;
    }
    callback({
      ...(request.videoRequested ? { video: selectedScreen } : {}),
      ...(request.audioRequested ? { audio: "loopback" } : {}),
    });
  }, { useSystemPicker: false });
  tray = new Tray(trayImage());
  updateTray();
  createWindow();
  startDesktopRegistrationLoop();

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
  stopNativeAudioStreams();
  const microphoneStarted = startNativeAudioProcess("microphone", options.microphoneSourceId || "native-microphone");
  const systemStarted = startNativeAudioProcess("system", options.systemSourceId || "native-system-output");
  return { ok: microphoneStarted || systemStarted, microphoneStarted, systemStarted };
});
ipcMain.handle("desktop:stop-native-audio-stream", async () => {
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
});

ipcMain.handle("desktop:upload-screenshot-capture", async (_event, request: {
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
  const response = await fetch(url, {
    method: "POST",
    body: form,
  });
  return {
    ok: response.ok,
    status: response.status,
    statusText: response.statusText,
    headers: Object.fromEntries(response.headers.entries()),
    bodyText: await response.text(),
  };
});

ipcMain.handle("desktop:open-external", async (_event, url: string) => {
  await shell.openExternal(url);
});

ipcMain.handle("desktop:probe-web-url", async (_event, url: string) => probeWebUrl(url));

ipcMain.handle("desktop:api-request", async (_event, request: { url: string; method?: string; headers?: Record<string, string>; body?: string | null }) => {
  const url = assertOfferSteadyApiUrl(request.url);
  const response = await fetch(url, {
    method: request.method ?? "GET",
    headers: request.headers,
    body: request.body ?? undefined,
  });
  return {
    ok: response.ok,
    status: response.status,
    statusText: response.statusText,
    headers: Object.fromEntries(response.headers.entries()),
    bodyText: await response.text(),
  };
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
});
