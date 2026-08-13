import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";
import {
  copyTextWithFallback,
  parseReferralActivationInput,
} from "./BillingPage";
import { interviewAppAdapter } from "./app-adapter";
import { syntheticState } from "./test-state";

const open = (path: string, authenticated = true) => {
  window.history.pushState({}, "", path);
  return render(
    <App
      initialAuthenticated={authenticated}
      initialState={structuredClone(syntheticState)}
    />,
  );
};

afterEach(() => vi.restoreAllMocks());

describe("device center and referral growth", () => {
  it.each([
    ["syntheticReferralCode", "syntheticReferralCode"],
    [
      "  https://mianshiwen.cn/invite/syntheticReferralCode  ",
      "syntheticReferralCode",
    ],
    ["/invite/syntheticReferralCode", "syntheticReferralCode"],
    ["https://mianshiwen.cn/app/billing", null],
    ["short", null],
  ])("parses referral activation input %s", (input, expected) => {
    expect(parseReferralActivationInput(input)).toBe(expected);
  });

  it("keeps device downloads without loading the linked-device center", () => {
    const listDesktopDevices = vi.spyOn(
      interviewAppAdapter,
      "listDesktopDevices",
    );
    open("/app/devices");
    expect(
      screen.getByRole("heading", { name: "下载电脑伴随程序" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "安装说明" })).toHaveAttribute(
      "href",
      "/app/guide#desktop",
    );
    expect(screen.queryByText("已关联设备")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "诊断" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "刷新状态" }),
    ).not.toBeInTheDocument();
    expect(listDesktopDevices).not.toHaveBeenCalled();
  });

  it("shows a stable referral link and aggregate rewards on billing", async () => {
    vi.spyOn(interviewAppAdapter, "getReferralStatus").mockResolvedValue({
      enabled: true,
      rewardPoints: 500,
      configVersion: 2,
      referralCode: "syntheticReferralCode",
      shareUrl: "https://example.test/invite/syntheticReferralCode",
      inviteCount: 3,
      totalRewardPoints: 1500,
      hasActivatedReferral: false,
    });
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });
    open("/app/billing");
    const section = (
      await screen.findByRole("heading", { name: "邀请好友，获得积分" })
    ).closest("section");
    expect(section).not.toBeNull();
    expect(section).toHaveTextContent("3成功邀请");
    expect(section).toHaveTextContent("1500累计奖励积分");
    expect(
      within(section!).getByDisplayValue(
        "https://example.test/invite/syntheticReferralCode",
      ),
    ).toHaveAttribute("readonly");
    fireEvent.click(within(section!).getByRole("button", { name: "复制链接" }));
    await waitFor(() =>
      expect(writeText).toHaveBeenCalledWith(
        "https://example.test/invite/syntheticReferralCode",
      ),
    );
    expect(
      await within(section!).findByRole("button", { name: "已复制" }),
    ).toBeInTheDocument();
  });

  it("falls back to the legacy copy command when Clipboard API is unavailable", async () => {
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: undefined,
    });
    const execCommand = vi.fn().mockReturnValue(true);
    Object.defineProperty(document, "execCommand", {
      configurable: true,
      value: execCommand,
    });

    await expect(
      copyTextWithFallback("https://example.test/invite/fallbackCode"),
    ).resolves.toBe(true);
    expect(execCommand).toHaveBeenCalledWith("copy");
    expect(document.querySelector("textarea[aria-hidden='true']")).toBeNull();
  });

  it("restores an invitation after login and activates it explicitly", async () => {
    vi.spyOn(interviewAppAdapter, "resolveReferral").mockResolvedValue({
      valid: true,
      enabled: true,
      rewardPoints: 500,
    });
    const activate = vi
      .spyOn(interviewAppAdapter, "activateReferral")
      .mockResolvedValue({
        outcome: "activated",
        replayed: false,
        rewardPoints: 500,
        activatedAtMs: Date.now(),
      });
    open("/invite/syntheticReferralCode", true);
    expect(await screen.findByText("500 点")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "确认激活邀请" }));
    expect(
      await screen.findByText("邀请已成功激活，奖励已发放给邀请人。"),
    ).toBeInTheDocument();
    expect(activate).toHaveBeenCalledWith(
      "syntheticReferralCode",
      expect.any(AbortSignal),
    );
  });

  it("activates a pasted referral link from billing and refreshes authoritative status", async () => {
    const initialStatus = {
      enabled: true,
      rewardPoints: 500,
      configVersion: 2,
      referralCode: "currentUsersReferralCode",
      shareUrl: "https://example.test/invite/currentUsersReferralCode",
      inviteCount: 0,
      totalRewardPoints: 0,
      hasActivatedReferral: false,
    };
    const getReferralStatus = vi
      .spyOn(interviewAppAdapter, "getReferralStatus")
      .mockResolvedValueOnce(initialStatus)
      .mockResolvedValue({ ...initialStatus, hasActivatedReferral: true });
    const activate = vi
      .spyOn(interviewAppAdapter, "activateReferral")
      .mockResolvedValue({
        outcome: "activated",
        replayed: false,
        rewardPoints: 500,
        activatedAtMs: Date.now(),
      });
    open("/app/billing");

    const input = await screen.findByLabelText("邀请链接或邀请码");
    fireEvent.change(input, {
      target: { value: "https://mianshiwen.cn/invite/friendsReferralCode" },
    });
    fireEvent.click(screen.getByRole("button", { name: "确认激活" }));

    await waitFor(() =>
      expect(activate).toHaveBeenCalledWith(
        "friendsReferralCode",
        expect.any(AbortSignal),
      ),
    );
    expect(
      await screen.findByText("邀请已成功激活，奖励已发放给邀请人。"),
    ).toBeInTheDocument();
    expect(
      await screen.findByText("已激活过邀请，不能再次激活其他链接。"),
    ).toBeInTheDocument();
    expect(getReferralStatus).toHaveBeenCalledTimes(2);
  });

  it("rejects malformed input locally and displays server self-referral feedback", async () => {
    vi.spyOn(interviewAppAdapter, "getReferralStatus").mockResolvedValue({
      enabled: true,
      rewardPoints: 500,
      configVersion: 2,
      referralCode: "currentUsersReferralCode",
      shareUrl: "https://example.test/invite/currentUsersReferralCode",
      inviteCount: 0,
      totalRewardPoints: 0,
      hasActivatedReferral: false,
    });
    const activate = vi
      .spyOn(interviewAppAdapter, "activateReferral")
      .mockResolvedValue({ outcome: "self-referral" });
    open("/app/billing");

    const input = await screen.findByLabelText("邀请链接或邀请码");
    fireEvent.change(input, { target: { value: "bad" } });
    fireEvent.click(screen.getByRole("button", { name: "确认激活" }));
    expect(
      await screen.findByText("请输入有效的邀请链接或邀请码。"),
    ).toBeInTheDocument();
    expect(activate).not.toHaveBeenCalled();

    fireEvent.change(input, { target: { value: "currentUsersReferralCode" } });
    fireEvent.click(screen.getByRole("button", { name: "确认激活" }));
    expect(
      await screen.findByText("不能激活自己的邀请链接。"),
    ).toBeInTheDocument();
  });

  it("does not render an activation form after the account has activated once", async () => {
    vi.spyOn(interviewAppAdapter, "getReferralStatus").mockResolvedValue({
      enabled: true,
      rewardPoints: 500,
      configVersion: 2,
      referralCode: "currentUsersReferralCode",
      shareUrl: "https://example.test/invite/currentUsersReferralCode",
      inviteCount: 0,
      totalRewardPoints: 0,
      hasActivatedReferral: true,
    });
    open("/app/billing");
    expect(
      await screen.findByText("已激活过邀请，不能再次激活其他链接。"),
    ).toBeInTheDocument();
    expect(screen.queryByLabelText("邀请链接或邀请码")).not.toBeInTheDocument();
  });

  it("keeps empty activation actionable and explains that a friend link is required", async () => {
    vi.spyOn(interviewAppAdapter, "getReferralStatus").mockResolvedValue({
      enabled: true,
      rewardPoints: 500,
      configVersion: 2,
      referralCode: "currentUsersReferralCode",
      shareUrl: "https://example.test/invite/currentUsersReferralCode",
      inviteCount: 0,
      totalRewardPoints: 0,
      hasActivatedReferral: false,
    });
    const activate = vi.spyOn(interviewAppAdapter, "activateReferral");
    open("/app/billing");

    const button = await screen.findByRole("button", { name: "确认激活" });
    expect(button).toBeEnabled();
    fireEvent.click(button);
    expect(
      await screen.findByText("请输入有效的邀请链接或邀请码。"),
    ).toBeInTheDocument();
    expect(activate).not.toHaveBeenCalled();
  });
});
