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
    render(<App initialAuthenticated={false} initialState={syntheticState} />);
    expect(await screen.findByRole("link", { name: "合作伙伴计划" })).toHaveAttribute("href", "/app/partner-program");
    expect(join).not.toHaveBeenCalled();
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
});
