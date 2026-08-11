import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";
import { interviewAppAdapter } from "./app-adapter";
import { syntheticState } from "./test-state";

const open = (path: string, authenticated = true) => {
  window.history.pushState({}, "", path);
  return render(<App initialAuthenticated={authenticated} initialState={structuredClone(syntheticState)} />);
};

afterEach(() => vi.restoreAllMocks());

describe("device center and referral growth", () => {
  it("renders truthful linked-device state and actionable diagnostics", async () => {
    vi.spyOn(interviewAppAdapter, "listDesktopDevices").mockResolvedValue([{
      deviceId: "device-synthetic",
      displayName: "测试 MacBook Pro",
      maskedManualCode: "••••35",
      capabilities: { platformVersion: "macOS 15.0", microphone: "granted", systemAudio: "granted", screenCapture: "denied" },
      online: false,
      lastSeenAtMs: 1_719_000_000_000,
      linkedAtMs: 1_718_000_000_000,
      lastUsedAtMs: 1_719_000_000_000,
      accountBound: true,
      devicePresence: "offline",
      permissionStatus: { microphone: "granted", systemAudio: "granted", screenCapture: "denied" },
      activeInterview: null,
    }]);
    open("/app/devices");
    const card = (await screen.findByText("测试 MacBook Pro")).closest("article");
    expect(card).not.toBeNull();
    expect(card).toHaveTextContent("离线");
    expect(card).toHaveTextContent("当前面试未连接");
    expect(card).not.toHaveTextContent("权限正常");
    fireEvent.click(within(card!).getByRole("button", { name: "诊断" }));
    expect(within(card!).getByText("麦克风").parentElement).toHaveTextContent("已授权");
    expect(within(card!).getByText("屏幕录制").parentElement).toHaveTextContent("未授权");
    expect(within(card!).getByRole("link", { name: "打开设备授权与故障排查" })).toHaveAttribute("href", "/app/guide#desktop");
  });

  it("shows a stable referral link and aggregate rewards on billing", async () => {
    vi.spyOn(interviewAppAdapter, "getReferralStatus").mockResolvedValue({
      enabled: true, rewardPoints: 500, configVersion: 2, referralCode: "syntheticReferralCode",
      shareUrl: "https://example.test/invite/syntheticReferralCode", inviteCount: 3,
      totalRewardPoints: 1500, hasActivatedReferral: false,
    });
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } });
    open("/app/billing");
    const section = (await screen.findByRole("heading", { name: "邀请好友，获得积分" })).closest("section");
    expect(section).not.toBeNull();
    expect(section).toHaveTextContent("3成功邀请");
    expect(section).toHaveTextContent("1500累计奖励积分");
    expect(within(section!).getByDisplayValue("https://example.test/invite/syntheticReferralCode")).toHaveAttribute("readonly");
    fireEvent.click(within(section!).getByRole("button", { name: "复制链接" }));
    await waitFor(() => expect(writeText).toHaveBeenCalledWith("https://example.test/invite/syntheticReferralCode"));
    expect(await within(section!).findByRole("button", { name: "已复制" })).toBeInTheDocument();
  });

  it("restores an invitation after login and activates it explicitly", async () => {
    vi.spyOn(interviewAppAdapter, "resolveReferral").mockResolvedValue({ valid: true, enabled: true, rewardPoints: 500 });
    const activate = vi.spyOn(interviewAppAdapter, "activateReferral").mockResolvedValue({ outcome: "activated", replayed: false, rewardPoints: 500, activatedAtMs: Date.now() });
    open("/invite/syntheticReferralCode", true);
    expect(await screen.findByText("500 点")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "确认激活邀请" }));
    expect(await screen.findByText("邀请已成功激活，奖励已发放给邀请人。")).toBeInTheDocument();
    expect(activate).toHaveBeenCalledWith("syntheticReferralCode", expect.any(AbortSignal));
  });
});
