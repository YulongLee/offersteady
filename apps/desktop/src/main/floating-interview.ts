import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { app, BrowserWindow, ipcMain, session, WebContentsView } from "electron";

export const floatingChromePartition = "offersteady-floating-chrome";
const sitePartition = "offersteady-floating-cn";
const cnOrigin = "https://mianshiwen.cn";
const headerHeight = 48;
const footerHeight = 28;
const rendererPath = path.resolve(__dirname, "../floating-preview");
export const floatingInterviewPage = path.join(rendererPath, "interview.html");

type LoadState = "loading" | "ready" | "failed";
type ProtectionState = "requested" | "unavailable" | "unsupported";
interface FloatingWindow {
  readonly window: BrowserWindow;
  readonly site: WebContentsView;
  status: LoadState;
  protection: ProtectionState;
  tuckedAway: boolean;
}

let interview: FloatingWindow | null = null;
let siteOrigin = cnOrigin;
let siteStyles = "";
let readManualCode: (() => Promise<string | null>) | undefined;

function trustedSite(url: string) {
  try {
    const parsed = new URL(url);
    return parsed.origin === siteOrigin && !parsed.username && !parsed.password;
  } catch {
    return false;
  }
}

function allowsSiteResource(url: string) {
  try {
    const parsed = new URL(url);
    if (parsed.protocol === "data:" || parsed.protocol === "blob:") return true;
    if (parsed.protocol === "ws:" || parsed.protocol === "wss:") {
      parsed.protocol = parsed.protocol === "wss:" ? "https:" : "http:";
    }
    return trustedSite(parsed.href);
  } catch {
    return false;
  }
}

function allowsChromeResource(url: string) {
  try {
    const parsed = new URL(url);
    if (parsed.protocol !== "file:") return false;
    const relative = path.relative(rendererPath, fileURLToPath(parsed));
    return relative !== ".." && !relative.startsWith(`..${path.sep}`) && !path.isAbsolute(relative);
  } catch {
    return false;
  }
}

// Serialized into an isolated world of the trusted preparation page.
function connectLocalCompanion(origin: string, pathname: string, manualCode: string) {
  let filled: HTMLInputElement | undefined;
  let settleTimer: number | undefined;
  let inputSettled = false;
  const onPreparationPage = () => location.origin === origin && location.pathname === pathname;
  const connect = () => {
    if (!onPreparationPage()) return true;
    const panel = document.querySelector(".machine-code-panel");
    const input = panel?.querySelector<HTMLInputElement>('input[inputmode="numeric"][maxlength="6"]');
    const button = panel?.querySelector<HTMLButtonElement>(":scope > button.button.ghost");
    if (!input || !button) return false;
    window.clearTimeout(discoveryTimeout);
    if (input.disabled || input.readOnly) return false;
    if (filled ? filled !== input || input.value !== manualCode : Boolean(input.value)) return true;
    if (button.disabled || !/^(验证并连接|验证连接)$/.test(button.textContent?.trim() ?? "")) return false;
    if (!filled) {
      const setValue = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set;
      if (!setValue) return true;
      filled = input;
      setValue.call(input, manualCode);
      input.dispatchEvent(new Event("input", { bubbles: true }));
      // Let the website commit its controlled input before invoking its own handler.
      settleTimer = window.setTimeout(() => {
        inputSettled = true;
        if (connect()) stop();
      }, 0);
      return false;
    }
    if (!inputSettled) return false;
    button.dataset.floatingLocalConnect = "";
    button.click();
    return true;
  };

  const stop = () => {
    observer.disconnect();
    window.clearTimeout(discoveryTimeout);
    window.clearTimeout(settleTimer);
    window.removeEventListener("pagehide", stop);
    window.navigation.removeEventListener("currententrychange", stopAfterNavigation);
  };
  const stopAfterNavigation = () => { if (!onPreparationPage()) stop(); };
  const observer = new MutationObserver(() => { if (connect()) stop(); });
  // Limit discovery, but keep waiting while the site asks the user to resolve a conflict.
  const discoveryTimeout = window.setTimeout(stop, 15000);
  observer.observe(document.documentElement, {
    childList: true,
    subtree: true,
    attributes: true,
    attributeFilter: ["disabled", "readonly"],
  });
  window.addEventListener("pagehide", stop, { once: true });
  window.navigation.addEventListener("currententrychange", stopAfterNavigation);
  if (connect()) stop();
}

export function requestWindowCaptureProtection(window: BrowserWindow): ProtectionState {
  if (process.platform !== "win32" && process.platform !== "darwin") return "unsupported";
  try {
    window.setContentProtection(true);
    return window.isContentProtected() ? "requested" : "unavailable";
  } catch {
    return "unavailable";
  }
}

function windowState(current: FloatingWindow) {
  return {
    productionBuild: app.isPackaged && existsSync(path.join(process.resourcesPath, "cn-floating-production")),
    transparency: Math.round((1 - current.window.getOpacity()) * 100),
    protection: current.protection,
    status: current.status,
    host: new URL(siteOrigin).host,
    canTuckAway: process.platform === "darwin",
  };
}

function resizeSite(current: FloatingWindow) {
  const { width, height } = current.window.getContentBounds();
  const ready = current.status === "ready";
  current.site.setBounds({
    x: 0,
    y: headerHeight,
    width: ready ? width : 0,
    height: ready ? Math.max(0, height - headerHeight - footerHeight) : 0,
  });
}

function setStatus(current: FloatingWindow, status: LoadState) {
  if (interview !== current || current.window.isDestroyed()) return;
  current.status = status;
  resizeSite(current);
  current.window.webContents.send("floating-preview:status", windowState(current));
}

function loadWorkspace(current: FloatingWindow) {
  setStatus(current, "loading");
  void current.site.webContents.loadURL(new URL("/app/interviews/new", siteOrigin).href).catch(() => undefined);
}

export function openFloatingInterview() {
  if (interview && !interview.window.isDestroyed()) {
    const { window } = interview;
    if (window.isMinimized()) window.restore();
    if (interview.tuckedAway) {
      interview.tuckedAway = false;
      window.show();
    }
    if (window.isVisible()) window.focus();
    return;
  }

  const window = new BrowserWindow({
    title: app.isPackaged && existsSync(path.join(process.resourcesPath, "cn-floating-production")) ? "桌面浮窗" : "桌面浮窗 · 国服测试",
    width: 650,
    height: 640,
    minWidth: 390,
    minHeight: 460,
    resizable: true,
    alwaysOnTop: true,
    show: false,
    backgroundColor: "#101c28",
    webPreferences: {
      partition: floatingChromePartition,
      preload: path.join(__dirname, "floating-preview-preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });
  const site = new WebContentsView({
    webPreferences: {
      partition: sitePartition,
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      // The live workspace suspends realtime subscriptions when the document becomes hidden.
      backgroundThrottling: process.platform !== "darwin",
    },
  });
  const current: FloatingWindow = {
    window, site, status: "loading", protection: requestWindowCaptureProtection(window), tuckedAway: false,
  };
  interview = current;
  window.removeMenu();
  window.webContents.setWindowOpenHandler(() => ({ action: "deny" }));
  window.webContents.on("will-frame-navigate", event => event.preventDefault());
  window.webContents.on("will-attach-webview", event => event.preventDefault());

  site.setBackgroundColor("#101c28");

  const contents = site.webContents;
  let navigation = 0;
  let preparationPath = "";
  const connectCompanion = () => {
    const url = contents.getURL();
    const pathname = trustedSite(url) ? new URL(url).pathname : "";
    if (preparationPath === pathname) return;
    preparationPath = pathname;
    if (!/^\/app\/interviews\/[^/]+\/prepare\/?$/.test(pathname) || !readManualCode) return;
    const documentNavigation = navigation;
    void readManualCode().then(code => {
      if (!code || !/^[0-9]{6}$/.test(code) || interview !== current || contents.isDestroyed()
          || navigation !== documentNavigation || preparationPath !== pathname) return;
      const active = contents.getURL();
      if (!trustedSite(active) || new URL(active).pathname !== pathname) return;
      return contents.executeJavaScriptInIsolatedWorld(1201, [{
        code: `(${connectLocalCompanion.toString()})(${JSON.stringify(siteOrigin)}, ${JSON.stringify(pathname)}, ${JSON.stringify(code)})`,
      }]);
    }).catch(() => undefined);
  };
  contents.setWindowOpenHandler(({ url }) => {
    if (trustedSite(url)) {
      queueMicrotask(() => {
        if (!contents.isDestroyed()) void contents.loadURL(url).catch(() => undefined);
      });
    }
    return { action: "deny" };
  });
  contents.on("will-frame-navigate", event => {
    if (!trustedSite(event.url)) event.preventDefault();
  });
  contents.on("will-redirect", event => {
    if (!trustedSite(event.url)) {
      event.preventDefault();
      if (event.isMainFrame) setStatus(current, "failed");
    }
  });
  contents.on("will-attach-webview", event => event.preventDefault());
  contents.on("did-start-navigation", event => {
    if (event.isMainFrame && !event.isSameDocument && trustedSite(event.url)) {
      navigation++;
      preparationPath = "";
      setStatus(current, "loading");
    }
  });
  contents.on("did-navigate", (_event, _url, code) => {
    if (code >= 400) setStatus(current, "failed");
  });
  contents.on("did-fail-load", (_event, code, _description, _url, mainFrame) => {
    if (mainFrame && code !== -3) setStatus(current, "failed");
  });
  contents.on("render-process-gone", () => setStatus(current, "failed"));
  contents.on("did-navigate-in-page", (_event, _url, mainFrame) => {
    if (mainFrame) connectCompanion();
  });
  contents.on("did-finish-load", () => {
    if (!trustedSite(contents.getURL()) || current.status === "failed") return;
    connectCompanion();
    const documentNavigation = navigation;
    void contents.insertCSS(siteStyles).catch(() => undefined).then(() => {
      if (navigation === documentNavigation && current.status !== "failed") setStatus(current, "ready");
    });
  });

  window.once("ready-to-show", () => {
    if (interview !== current || window.isDestroyed()) return;
    window.show();
    window.contentView.addChildView(site);
    window.on("resize", () => resizeSite(current));
    loadWorkspace(current);
  });
  window.once("closed", () => {
    if (interview === current) interview = null;
    if (!contents.isDestroyed()) contents.close({ waitForBeforeUnload: false });
  });
  void window.loadFile(floatingInterviewPage).catch(() => {
    if (!window.isDestroyed()) window.destroy();
  });
}

function ownedWindow(event: Electron.IpcMainInvokeEvent) {
  const current = interview;
  if (!current || current.window.isDestroyed() || event.sender !== current.window.webContents
      || event.senderFrame !== current.window.webContents.mainFrame) {
    throw new Error("Invalid floating window sender");
  }
  return current;
}

export function initializeFloatingInterview(
  loopbackWorkspaceUrl: string | undefined,
  loadManualCode: () => Promise<string | null>,
) {
  readManualCode = loadManualCode;
  siteOrigin = loopbackWorkspaceUrl ? new URL(loopbackWorkspaceUrl).origin : cnOrigin;
  siteStyles = readFileSync(path.join(rendererPath, "online-site.css"), "utf8");
  const chrome = session.fromPartition(floatingChromePartition);
  const site = session.fromPartition(sitePartition);
  for (const isolated of [chrome, site]) {
    isolated.setPermissionCheckHandler(() => false);
    isolated.setPermissionRequestHandler((_contents, _permission, callback) => callback(false));
    isolated.setDisplayMediaRequestHandler((_request, callback) => callback({}));
  }
  chrome.webRequest.onBeforeRequest((details, callback) => callback({ cancel: !allowsChromeResource(details.url) }));
  site.webRequest.onBeforeRequest((details, callback) => callback({ cancel: !allowsSiteResource(details.url) }));

  ipcMain.handle("floating-preview:state", event => windowState(ownedWindow(event)));
  ipcMain.handle("floating-preview:transparency", (event, percentage: unknown) => {
    const current = ownedWindow(event);
    if (typeof percentage !== "number" || !Number.isInteger(percentage) || percentage < 0 || percentage > 60) {
      throw new RangeError("Preview transparency must be an integer from 0 through 60");
    }
    current.window.setOpacity(1 - percentage / 100);
    current.protection = requestWindowCaptureProtection(current.window);
    return windowState(current);
  });
  ipcMain.handle("floating-preview:retry", event => {
    const current = ownedWindow(event);
    if (current.status === "failed") loadWorkspace(current);
  });
  ipcMain.handle("floating-preview:tuck-away", event => {
    const current = ownedWindow(event);
    if (process.platform !== "darwin") throw new Error("Floating window tuck away requires macOS");
    current.tuckedAway = true;
    current.window.hide();
  });
}
