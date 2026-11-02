// @vitest-environment jsdom
import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CompanionApp } from "../src/renderer/CompanionApp";

const fakes = vi.hoisted(() => ({
  mode: "mock", monitorStart: vi.fn(), monitorStop: vi.fn(), mockStart: vi.fn(), mockStop: vi.fn(),
  monitors: [] as unknown[], microphoneOptions: [] as {
    onPermission: (value: boolean) => void;
    onState: (state: "capturing" | "paused" | "error", message: string) => void;
  }[],
}));
vi.mock("../src/renderer/audio/audio-source-adapter", () => ({
  MicrophoneAudioAdapter: class { listSources = async () => [{ id: "default", kind: "microphone", label: "Synthetic microphone", available: true }]; },
  SystemAudioAdapter: class {}, describeMediaError: () => "Synthetic media unavailable",
}));
vi.mock("../src/renderer/audio/local-source-monitor", () => ({
  LocalSourceMonitor: class {
    constructor(options: unknown) { fakes.monitors.push(options); }
    start = fakes.monitorStart; stop = fakes.monitorStop;
  },
}));
vi.mock("../src/renderer/audio/mock-microphone", () => ({
  MockMicrophone: class {
    constructor(options: { onPermission: (value: boolean) => void; onState: (state: "capturing" | "paused" | "error", message: string) => void }) { fakes.microphoneOptions.push(options); }
    start = fakes.mockStart; stop = fakes.mockStop;
  },
}));

const deferred = <T>() => {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>(done => { resolve = done; });
  return { promise, resolve };
};
const permission = (value: string) => ({ permission: value, pending: false, source: "os" });
const settle = async () => { for (let i = 0; i < 25; i++) await Promise.resolve(); };
let root: Root | null;
let host: HTMLDivElement;
let registrations: { capabilities: { microphone: string; systemAudio: string } }[];
let api: Record<string, ReturnType<typeof vi.fn>>;
let getUserMedia: ReturnType<typeof vi.fn>;
const flush = async () => { await act(settle); };
const mount = async () => {
  root = createRoot(host); await act(async () => { root!.render(createElement(CompanionApp)); await settle(); });
  await flush(); await flush();
};
const click = async (text: string) => {
  const button = [...host.querySelectorAll("button")].find(item => item.textContent === text);
  expect(button).toBeTruthy(); await act(async () => { button!.click(); await settle(); }); await flush();
};

beforeEach(() => {
  vi.useFakeTimers(); vi.clearAllMocks(); vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
  fakes.mode = "mock"; fakes.monitors = []; fakes.microphoneOptions = [];
  fakes.monitorStart.mockResolvedValue(undefined); fakes.monitorStop.mockResolvedValue(undefined); fakes.mockStop.mockResolvedValue(undefined);
  host = document.createElement("div"); document.body.append(host); root = null; registrations = [];
  getUserMedia = vi.fn(async () => ({ getAudioTracks: () => [1], getTracks: () => [{ stop: vi.fn() }] }));
  vi.stubGlobal("navigator", { mediaDevices: { getUserMedia, addEventListener: vi.fn(), removeEventListener: vi.fn() } });
  vi.stubGlobal("fetch", vi.fn(() => { throw new Error("unexpected-external-fetch"); }));
  api = {
    getDesktopConfig: vi.fn(async () => ({ appVersion: "1.3.6", platform: "windows", architecture: "x64", platformVersion: "synthetic", protocolVersion: "2.0", captureRuntime: "electron-single-owner", apiBaseUrl: "https://synthetic.invalid/api/v1", webWorkspaceUrl: "https://synthetic.invalid/app", realtimeEndpointing: { mode: "commercial-adaptive" } })),
    getPairingIdentity: vi.fn(async () => ({ deviceId: "synthetic-device", manualCode: "000000", displayName: "Synthetic" })),
    getNativeRuntimeHealth: vi.fn(async () => ({ available: true, ready: false, microphonePermission: "unknown" })),
    getMicrophonePermission: vi.fn(async () => permission("unknown")),
    requestMicrophonePermission: vi.fn(async () => permission("unknown")),
    requestMicrophoneAccess: vi.fn(async () => true),
    requestScreenCaptureAccess: vi.fn(async () => false),
    publishCaptureState: vi.fn(),
    apiRequest: vi.fn(async (request: { url: string; body?: string }) => {
      let data: unknown = {};
      if (request.url.endsWith("/desktop-devices/register")) registrations.push(JSON.parse(request.body!));
      else if (request.url.includes("/active-connection")) data = {
        state: "bound", registered: true, bound: true, sessionStatus: "preparing", sessionMode: fakes.mode, captureState: "paused",
        binding: { bindingId: "synthetic-binding", bindingGeneration: 1, sessionId: "synthetic-session", ownerUserId: "synthetic-owner", deviceId: "synthetic-device", manualCode: "000000", capabilities: {}, status: "bound" },
      };
      return { ok: true, status: 200, statusText: "OK", headers: {}, bodyText: JSON.stringify({ data }) };
    }),
  };
  Object.defineProperty(window, "offersteady", { configurable: true, value: api });
});
afterEach(async () => {
  if (root) await act(async () => { root!.unmount(); await settle(); });
  host.remove(); vi.unstubAllGlobals(); vi.useRealTimers();
});

describe("companion permission and mock-only integration", () => {
  it("syncs a late grant once before the next periodic cycle and does not open media or call the old Windows boolean", async () => {
    const late = deferred<unknown>(); api.getMicrophonePermission!.mockResolvedValue(permission("prompt")); api.requestMicrophonePermission!.mockImplementation(() => late.promise);
    await mount();
    expect(registrations.every(value => value.capabilities.microphone !== "granted")).toBe(true);
    await act(async () => { await vi.advanceTimersByTimeAsync(2501); await settle(); });
    expect(host.textContent).toContain("等待模拟面试收音"); expect(host.textContent).not.toContain("麦克风未授权");
    expect(host.textContent).not.toContain("重新检查"); expect(host.querySelector('[role="status"]')).toBeNull();
    expect(registrations.every(value => value.capabilities.microphone !== "granted" && value.capabilities.microphone !== "denied")).toBe(true);
    registrations = []; late.resolve(permission("granted")); await flush(); await flush();
    expect(registrations).toHaveLength(1); expect(registrations[0]!.capabilities.microphone).toBe("granted");
    expect(api.requestMicrophonePermission).toHaveBeenCalledOnce(); expect(api.requestMicrophoneAccess).not.toHaveBeenCalled(); expect(getUserMedia).not.toHaveBeenCalled();
  });

  it("preserves the original microphone row and its existing error retry never asks screen permission", async () => {
    await mount();
    expect(host.textContent).not.toContain("电脑输出"); expect(host.textContent).not.toContain("屏幕捕捉");
    const rowControl = host.querySelector(".terminal-row .row-control-main")!;
    expect([...rowControl.children].map(element => element.tagName)).toEqual(["SELECT"]);
    expect(rowControl.querySelector("button")).toBeNull();
    expect(host.textContent).not.toContain("重新检查"); expect(host.querySelector('[role="status"]')).toBeNull();
    const screenChecks = api.requestScreenCaptureAccess!.mock.calls.length;
    await act(async () => { fakes.microphoneOptions[0]!.onState("error", "模拟面试麦克风暂不可用，请重试麦克风。"); await settle(); });
    await click("重试麦克风");
    expect(getUserMedia).toHaveBeenCalledOnce(); expect(api.requestScreenCaptureAccess).toHaveBeenCalledTimes(screenChecks);
    expect(fakes.mockStart).toHaveBeenCalledTimes(2);
    expect(registrations.at(-1)!.capabilities.microphone).toBe("granted");
  });

  it("retains ordinary microphone, system audio and screenshot controls", async () => {
    fakes.mode = "interview"; await mount();
    expect(host.textContent).toContain("电脑输出"); expect(host.textContent).toContain("屏幕捕捉");
    expect(host.textContent).toContain("预览"); expect(host.textContent).toContain("快捷键");
    const rowControl = host.querySelector(".terminal-row .row-control-main")!;
    expect([...rowControl.children].map(element => element.tagName)).toEqual(["SELECT"]);
    expect(fakes.mockStart).not.toHaveBeenCalled();
    expect(fakes.monitors.some((value: any) => value.enabledChannels.join(",") === "microphone,system")).toBe(true);
  });

  it("registers actual mock denial immediately and cannot be overwritten by an older pending grant", async () => {
    const late = deferred<unknown>(); api.getMicrophonePermission!.mockResolvedValue(permission("prompt")); api.requestMicrophonePermission!.mockImplementation(() => late.promise);
    await mount(); registrations = [];
    await act(async () => {
      fakes.microphoneOptions[0]!.onPermission(false);
      fakes.microphoneOptions[0]!.onState("error", "模拟面试麦克风权限被拒绝，请重试麦克风。");
      await settle();
    }); await flush();
    expect(registrations.at(-1)!.capabilities.microphone).toBe("denied");
    late.resolve(permission("granted")); await flush();
    expect(registrations.at(-1)!.capabilities.microphone).toBe("denied"); expect(host.textContent).toContain("麦克风权限被拒绝");
    expect([...host.querySelectorAll("button")].some(button => button.textContent === "重试麦克风")).toBe(true);
  });

  it("ignores late permission results after unmount without another registration", async () => {
    const late = deferred<unknown>(); api.getMicrophonePermission!.mockResolvedValue(permission("prompt")); api.requestMicrophonePermission!.mockImplementation(() => late.promise);
    await mount(); await act(async () => { root!.unmount(); root = null; await settle(); });
    const before = registrations.length; late.resolve(permission("granted")); await flush();
    expect(registrations).toHaveLength(before); expect(getUserMedia).not.toHaveBeenCalled();
  });
});
