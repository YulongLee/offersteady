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
  it("keeps device downloads without loading the linked-device center", () => {
    const listDesktopDevices = vi.spyOn(interviewAppAdapter, "listDesktopDevices");
    open("/app/devices");
    expect(screen.getByRole("heading", { name: "下载电脑伴随程序" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "安装说明" })).toHaveAttribute("href", "/app/guide#desktop");
    expect(screen.queryByText("已关联设备")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "诊断" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "刷新状态" })).not.toBeInTheDocument();
    expect(listDesktopDevices).not.toHaveBeenCalled();
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
