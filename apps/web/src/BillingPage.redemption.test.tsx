import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { PointsRedemptionResult } from "@offersteady/protocol";
import { App } from "./App";
import { interviewAppAdapter } from "./app-adapter";
import { syntheticState } from "./test-state";

const success = (outcome: "redeemed" | "already-redeemed-by-you" = "redeemed"): PointsRedemptionResult => ({ outcome, data: { redemptionId: "synthetic-redemption-result", points: 120, newBalance: 320, publicHint: "••••-DEMO", redeemedAtMs: 1_800_000_000_000, ledgerEntry: { id: "synthetic-redemption-ledger", userId: "prototype-user", kind: "redemption_credit", points: 120, createdAtMs: 1_800_000_000_000, referenceId: "synthetic-redemption-result", description: "兑换码 ••••-DEMO 到账" } } });

const open = () => { window.history.pushState({}, "", "/app/billing"); return render(<App initialAuthenticated initialState={structuredClone(syntheticState)} />); };
const inputCode = (value = "SYNTHETIC-DEMO") => fireEvent.change(screen.getByLabelText("积分兑换码"), { target: { value } });

afterEach(() => vi.restoreAllMocks());

describe("billing points redemption", () => {
  it("starts empty with an accessible disabled action and no checkout", () => {
    open(); expect(screen.getByRole("button", { name: "立即兑换" })).toBeDisabled(); expect(screen.getByText(/输入 16 位兑换码/)).toBeInTheDocument(); expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("submits only code and generated idempotency metadata from the form keyboard path", async () => {
    const redeem = vi.spyOn(interviewAppAdapter, "redeemPoints").mockResolvedValue(success()); open(); inputCode(); fireEvent.submit(screen.getByLabelText("积分兑换码").closest("form")!);
    await waitFor(() => expect(redeem).toHaveBeenCalledOnce()); const request = redeem.mock.calls[0]![0]; expect(Object.keys(request).sort()).toEqual(["code", "idempotencyKey"]); expect(request).not.toHaveProperty("points");
  });

  it("prevents duplicate clicks while pending and preserves balance", () => {
    vi.spyOn(interviewAppAdapter, "redeemPoints").mockImplementation(() => new Promise(() => undefined)); open(); inputCode(); fireEvent.click(screen.getByRole("button", { name: "立即兑换" }));
    expect(screen.getByRole("button", { name: "兑换中…" })).toBeDisabled(); expect(screen.getByText("200 点", { selector: ".balance-card strong" })).toBeInTheDocument();
  });

  it("updates authoritative balance and history, then clears plaintext input", async () => {
    vi.spyOn(interviewAppAdapter, "redeemPoints").mockResolvedValue(success()); open(); inputCode(); fireEvent.click(screen.getByRole("button", { name: "立即兑换" }));
    expect(await screen.findByText(/兑换成功：\+120 点/)).toBeInTheDocument(); expect(screen.getByText("320 点", { selector: ".balance-card strong" })).toBeInTheDocument(); expect(screen.getByLabelText("积分兑换码")).toHaveValue("");
    expect(within(screen.getByRole("heading", { name: "积分明细" }).closest("section")!).getByText("+120 点")).toBeInTheDocument();
  });

  it("renders safe owner replay, unavailable and rate-limit states", async () => {
    const redeem = vi.spyOn(interviewAppAdapter, "redeemPoints").mockResolvedValueOnce(success("already-redeemed-by-you")).mockResolvedValueOnce({ outcome: "code-unavailable" }).mockResolvedValueOnce({ outcome: "rate-limited", retryAfterMs: 30_000 }); open();
    inputCode(); fireEvent.click(screen.getByRole("button", { name: "立即兑换" })); expect(await screen.findByText(/已兑换至当前账号/)).toBeInTheDocument();
    inputCode("SYNTHETIC-MISSING"); fireEvent.click(screen.getByRole("button", { name: "立即兑换" })); expect(await screen.findByText(/兑换码不可用/)).toBeInTheDocument();
    inputCode("SYNTHETIC-LIMIT"); fireEvent.click(screen.getByRole("button", { name: "立即兑换" })); expect(await screen.findByText(/约 30 秒后重试/)).toBeInTheDocument(); expect(redeem).toHaveBeenCalledTimes(3);
  });

  it("keeps failed input in memory for a retry after a network failure", async () => {
    vi.spyOn(interviewAppAdapter, "redeemPoints").mockRejectedValue(new Error("synthetic network failure")); open(); inputCode("SYNTHETIC-OUTAGE"); fireEvent.click(screen.getByRole("button", { name: "立即兑换" }));
    expect(await screen.findByText(/服务暂时不可用/)).toBeInTheDocument(); expect(screen.getByLabelText("积分兑换码")).toHaveValue("SYNTHETIC-OUTAGE"); expect(location.href).not.toContain("SYNTHETIC-OUTAGE");
  });
});
