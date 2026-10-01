// @vitest-environment jsdom
import { createElement } from "react";
import { act, cleanup, fireEvent, render, renderHook, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import path from "node:path";
import { useMicrophonePermission } from "../src/renderer/use-microphone-permission";
import { CompanionApp } from "../src/renderer/CompanionApp";

// This suite never acquires real audio or contacts a service.
vi.mock("../src/renderer/audio/local-source-monitor", () => ({
  LocalSourceMonitor: class {
    async start() {}
    async stop() {}
  },
}));

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

const installBridge = (extra: Record<string, unknown> = {}) => {
  const bridge = {
    getNativeRuntimeHealth: vi.fn(async () => ({ microphonePermission: "granted", ready: true, available: true })),
    requestMicrophoneAccess: vi.fn(async () => true),
    openPermissionSettings: vi.fn(async () => {}),
    ...extra,
  };
  Object.defineProperty(window, "offersteady", { configurable: true, value: bridge });
  return bridge;
};

describe("permission recovery without a redesigned assistant", () => {
  it("requests independently of registration and refreshes on focus without rendering UI", async () => {
    let status = "not-determined";
    const request = vi.fn(async () => { status = "granted"; return true; });
    installBridge({
      getNativeRuntimeHealth: async () => ({ microphonePermission: status }),
      requestMicrophoneAccess: request,
    });
    const onPermission = vi.fn();
    const { result } = renderHook(() => useMicrophonePermission(true, onPermission));
    await waitFor(() => expect(onPermission).toHaveBeenLastCalledWith("granted"));
    expect(request).toHaveBeenCalledTimes(1);
    expect(document.body.textContent).toBe("");
    status = "denied";
    fireEvent(window, new Event("focus"));
    await waitFor(() => expect(onPermission).toHaveBeenLastCalledWith("denied"));
    status = "granted";
    await act(async () => { await result.current.refresh(); });
    expect(onPermission).toHaveBeenLastCalledWith("granted");
    expect(request).toHaveBeenCalledTimes(1);
  });

  it("retries a failed initial check through the existing control action", async () => {
    let status = "not-determined";
    let reads = 0;
    const request = vi.fn(async () => { status = "granted"; return true; });
    installBridge({
      getNativeRuntimeHealth: async () => { if (++reads === 1) throw Error("synthetic IPC failure"); return { microphonePermission: status }; },
      requestMicrophoneAccess: request,
    });
    const onPermission = vi.fn();
    const { result } = renderHook(() => useMicrophonePermission(true, onPermission));
    await waitFor(() => expect(onPermission).toHaveBeenLastCalledWith("error"));
    await act(async () => { await result.current.refresh(); });
    await waitFor(() => expect(onPermission).toHaveBeenLastCalledWith("granted"));
    expect(request).toHaveBeenCalledTimes(1);
  });

  it("does not activate the Mac permission workflow on Windows or before configuration", async () => {
    const bridge = installBridge();
    const onPermission = vi.fn();
    const { result } = renderHook(() => useMicrophonePermission(false, onPermission));
    fireEvent(window, new Event("focus"));
    await act(async () => { await result.current.refresh(); });
    expect(bridge.getNativeRuntimeHealth).not.toHaveBeenCalled();
    expect(bridge.requestMicrophoneAccess).not.toHaveBeenCalled();
    expect(onPermission).not.toHaveBeenCalled();
  });

  it("removes listeners and ignores late checks on unmount", async () => {
    const read = vi.fn(async () => ({ microphonePermission: "granted" }));
    installBridge({ getNativeRuntimeHealth: read });
    const onPermission = vi.fn();
    const { unmount } = renderHook(() => useMicrophonePermission(true, onPermission));
    await waitFor(() => expect(onPermission).toHaveBeenCalledWith("granted"));
    unmount();
    fireEvent(window, new Event("focus"));
    fireEvent(document, new Event("visibilitychange"));
    expect(read).toHaveBeenCalledTimes(1);
  });

  it.each(["macos", "windows"])("preserves the original rows and buttons on %s", async platform => {
    const getPairingIdentity = vi.fn(async () => { throw Error("synthetic offline device"); });
    const bridge = installBridge({
      getDesktopConfig: async () => ({ platform, architecture: "x64", appVersion: "1.3.4", apiBaseUrl: "https://example.invalid/api/v1", webWorkspaceUrl: "https://example.invalid/app", realtimeEndpointing: { mode: "legacy-threshold" } }),
      getPairingIdentity,
      listScreens: async () => [],
      publishCaptureState: vi.fn(),
    });
    const fetch = vi.fn(() => { throw Error("unexpected network request"); });
    vi.stubGlobal("fetch", fetch);
    const { container } = render(createElement(CompanionApp));
    await waitFor(() => expect(getPairingIdentity).toHaveBeenCalled());
    if (platform === "macos") await waitFor(() => expect(screen.getByLabelText("选择麦克风").getAttribute("title")).toContain("已允许"));
    expect([...container.querySelectorAll(".terminal-row h2")].map(node => node.textContent)).toEqual(["麦克风", "电脑输出", "屏幕捕捉"]);
    expect(container.querySelector(".microphone-permission-panel")).toBeNull();
    expect(screen.getAllByRole("button").map(node => node.textContent)).toEqual([
      "预览", "快捷键未生效 · 点击设置", "连接码：------", "打开面试稳网站", "面试稳首页", "使用教程",
    ]);
    expect(container.querySelector(".terminal-rows")?.lastElementChild?.className).toBe("connection-card");
    fireEvent.click(screen.getByLabelText("选择麦克风"));
    await act(async () => {});
    expect(bridge.requestMicrophoneAccess).not.toHaveBeenCalled();
    expect(fetch).not.toHaveBeenCalled();
  });

  it("keeps the complete original stylesheet and has no timeout or panel mount", () => {
    const stylesheet = readFileSync(path.resolve(import.meta.dirname, "../src/renderer/styles.css"));
    // Released 1.3.2 stylesheet at fa9db78; permission repair must not redesign it.
    expect(createHash("sha256").update(stylesheet).digest("hex")).toBe("92280192e06984f1a64ca6cf847cf9306d1c2a3080b3273b0c9f7d2ff802f4fb");
    const app = readFileSync(path.resolve(import.meta.dirname, "../src/renderer/CompanionApp.tsx"), "utf8");
    expect(app).not.toContain("MicrophonePermissionPanel");
    expect(app).not.toContain("requestMicrophoneAccessInBackground");
    expect(app).toContain('useMicrophonePermission(config?.platform === "macos"');
    expect(app).not.toContain("mockInterviewProtocol");
  });
});
