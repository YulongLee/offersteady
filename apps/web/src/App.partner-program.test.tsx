import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";
import { interviewAppAdapter } from "./app-adapter";
import { syntheticState } from "./test-state";


describe("partner program", () => {
  beforeEach(() => {
    window.history.replaceState({}, "", "/");
    vi.restoreAllMocks();
  });

  it("exposes the homepage entry without enrolling the visitor", async () => {
    const join = vi.spyOn(interviewAppAdapter, "joinPartnerProgram");
    vi.spyOn(interviewAppAdapter, "getPartnerProgramConfig").mockResolvedValue({ enabled: true, configVersion: 1, commissionRateBps: 2000, eligibleOrderDays: 90, refundHoldDays: 7, minimumPayoutCents: 10000, agreementVersion: "2026-09-v1", settlementMode: "manual-monthly" });
    render(<App initialAuthenticated={false} initialState={syntheticState} />);
    expect(await screen.findByRole("link", { name: /了解合作伙伴计划/ })).toHaveAttribute("href", "/app/partner-program");
    expect(join).not.toHaveBeenCalled();
  });

  it("hides the homepage entry when the operator pauses the activity", async () => {
    vi.spyOn(interviewAppAdapter, "getPartnerProgramConfig").mockResolvedValue({ enabled: false, configVersion: 2, commissionRateBps: 2000, eligibleOrderDays: 90, refundHoldDays: 7, minimumPayoutCents: 10000, agreementVersion: "2026-09-v1", settlementMode: "manual-monthly" });
    render(<App initialAuthenticated={false} initialState={syntheticState} />);
    await waitFor(() => expect(interviewAppAdapter.getPartnerProgramConfig).toHaveBeenCalled());
    expect(screen.queryByRole("link", { name: /合作伙伴计划/ })).toBeNull();
  });

  it("does not add the partner program to authenticated workbench navigation", async () => {
    window.history.replaceState({}, "", "/app");
    render(<App initialAuthenticated initialState={syntheticState} />);
    expect(await screen.findByRole("heading", { name: "继续这场面试" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "合作伙伴计划" })).toBeNull();
  });

  it("requires explicit agreement before joining", async () => {
    window.history.replaceState({}, "", "/app/partner-program");
    vi.spyOn(interviewAppAdapter, "getPartnerProgram").mockResolvedValue({ joined: false, config: { enabled: true, commissionRateBps: 2000, eligibleOrderDays: 90, refundHoldDays: 7, minimumPayoutCents: 10000, agreementVersion: "2026-09-v1", settlementMode: "manual-monthly" } });
    const join = vi.spyOn(interviewAppAdapter, "joinPartnerProgram").mockResolvedValue({ joined: true, shareUrl: "https://example.test/r/safePartnerSlug", config: { enabled: true, commissionRateBps: 2000, eligibleOrderDays: 90, refundHoldDays: 7, minimumPayoutCents: 10000, agreementVersion: "2026-09-v1", settlementMode: "manual-monthly" }, profile: { status: "active", joinedAtMs: 1, agreementVersion: "2026-09-v1" }, metrics: { validVisitors: 0, registrations: 0, payingUsers: 0, attributedReceiptsCents: 0 }, balances: { pendingCents: 0, availableCents: 0, reservedCents: 0, settledCents: 0, refreshedAtMs: null }, payouts: [] });
    render(<App initialAuthenticated initialState={syntheticState} />);
    const button = await screen.findByRole("button", { name: "加入合作伙伴计划" });
    expect(button).toBeDisabled();
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(button);
    await waitFor(() => expect(join).toHaveBeenCalledWith("2026-09-v1"));
    expect(await screen.findByText("你的专属推广链接")).toBeInTheDocument();
  });

  it("does not hide a negative carry-forward after a post-settlement refund", async () => {
    window.history.replaceState({}, "", "/app/partner-program");
    vi.spyOn(interviewAppAdapter, "getPartnerProgram").mockResolvedValue({ joined: true, shareUrl: "https://example.test/r/safePartnerSlug", config: { enabled: true, commissionRateBps: 2000, eligibleOrderDays: 90, refundHoldDays: 7, minimumPayoutCents: 10000, agreementVersion: "2026-09-v1", settlementMode: "manual-monthly" }, profile: { status: "active", joinedAtMs: 1, agreementVersion: "2026-09-v1" }, metrics: { validVisitors: 1, registrations: 1, payingUsers: 1, attributedReceiptsCents: 1000 }, balances: { pendingCents: 0, availableCents: -100, reservedCents: 0, settledCents: 2000, refreshedAtMs: 1 }, payouts: [] });
    render(<App initialAuthenticated initialState={syntheticState} />);
    expect(await screen.findByText("-¥1.00")).toBeInTheDocument();
  });

  it("collects only manual payout details and keeps them masked after saving", async () => {
    window.history.replaceState({}, "", "/app/partner-program");
    const base = { joined: true, shareUrl: "https://example.test/r/safePartnerSlug", config: { enabled: true, commissionRateBps: 2000, eligibleOrderDays: 90, refundHoldDays: 7, minimumPayoutCents: 10000, agreementVersion: "2026-09-v1", settlementMode: "manual-monthly" as const, payoutProfileEnabled: true }, profile: { status: "active" as const, joinedAtMs: 1, agreementVersion: "2026-09-v1" }, metrics: { validVisitors: 0, registrations: 0, payingUsers: 0, attributedReceiptsCents: 0 }, balances: { pendingCents: 0, availableCents: 0, reservedCents: 0, settledCents: 0, refreshedAtMs: 1 }, payouts: [] };
    vi.spyOn(interviewAppAdapter, "getPartnerProgram").mockResolvedValue(base);
    const save = vi.spyOn(interviewAppAdapter, "savePartnerPayoutProfile").mockResolvedValue({ payoutProfileId: "profile-1", version: 1, payoutMethod: "alipay", maskedAccountName: "测*", maskedAccountIdentifier: "****1234", updatedAtMs: 1 });
    render(<App initialAuthenticated initialState={syntheticState} />);
    await screen.findByText("人工结算收款信息");
    fireEvent.change(screen.getByLabelText("实名姓名"), { target: { value: "测试用户" } });
    fireEvent.change(screen.getByLabelText("收款账号"), { target: { value: "test-account-1234" } });
    fireEvent.click(screen.getByRole("button", { name: "保存收款信息" }));
    await waitFor(() => expect(save).toHaveBeenCalledWith({ payoutMethod: "alipay", accountName: "测试用户", accountIdentifier: "test-account-1234" }));
    expect(screen.getByText(/不会自动发起支付宝或微信转账/)).toBeInTheDocument();
  });
});
