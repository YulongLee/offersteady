// @vitest-environment jsdom
import { createElement } from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MicrophonePermissionPanel } from "../src/renderer/MicrophonePermissionPanel";
import { readFileSync } from "node:fs";
import path from "node:path";

afterEach(cleanup);

describe("microphone permission recovery UI", () => {
  it("requests permission without backend calls and refreshes on focus", async () => {
    let status = "not-determined";
    const request = vi.fn(async () => { status = "granted"; return true; });
    const openSettings = vi.fn(async () => {});
    Object.defineProperty(window, "offersteady", { configurable: true, value: {
      getNativeRuntimeHealth: async () => ({ microphonePermission: status }),
      requestMicrophoneAccess: request, openPermissionSettings: openSettings,
    } });
    const onPermission = vi.fn();
    render(createElement(MicrophonePermissionPanel, { onPermission }));
    await waitFor(() => expect(onPermission).toHaveBeenLastCalledWith("granted"));
    expect(request).toHaveBeenCalledTimes(1);
    status = "denied";
    fireEvent(window, new Event("focus"));
    await waitFor(() => expect(screen.getByRole("status").textContent).toContain("已拒绝"));
    expect(screen.queryByText("申请麦克风授权")).toBeNull();
    fireEvent.click(screen.getByText("打开系统设置"));
    await waitFor(() => expect(openSettings).toHaveBeenCalledWith("microphone"));
    status = "granted";
    fireEvent.click(screen.getByText("检查权限"));
    await waitFor(() => expect(onPermission).toHaveBeenLastCalledWith("granted"));
  });

  it("offers a real retry action when the initial status check fails", async () => {
    let reads = 0;
    const request = vi.fn(async () => true);
    Object.defineProperty(window, "offersteady", { configurable: true, value: {
      getNativeRuntimeHealth: async () => { if (++reads === 1) throw Error("IPC"); return { microphonePermission: "granted" }; },
      requestMicrophoneAccess: request, openPermissionSettings: vi.fn(),
    } });
    render(createElement(MicrophonePermissionPanel, { onPermission: vi.fn() }));
    fireEvent.click(await screen.findByText("申请麦克风授权"));
    await waitFor(() => expect(screen.getByRole("status").textContent).toContain("已允许"));
    expect(request).toHaveBeenCalledTimes(1);
  });

  it("mounts only for macOS and removes the former timeout path", () => {
    const app = readFileSync(path.resolve(import.meta.dirname, "../src/renderer/CompanionApp.tsx"), "utf8");
    expect(app).toContain('config?.platform === "macos" && <MicrophonePermissionPanel');
    expect(app).not.toContain("requestMicrophoneAccessInBackground");
    expect(app).not.toContain("const refreshAuthorization");
    expect(app).not.toContain("mockInterviewProtocol");
    expect(app).toContain("microphoneAuthorized");
  });
});
