import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { readFileSync } from "node:fs";
import type { OfficialCheckoutOrder, PointsLedgerEntry, PointsRedemptionResult } from "@offersteady/protocol";
import { App } from "./App";
import { summarizePointsLedger } from "./BillingPage";
import { interviewAppAdapter } from "./app-adapter";
import { syntheticState } from "./test-state";

const success = (outcome: "redeemed" | "already-redeemed-by-you" = "redeemed"): PointsRedemptionResult => ({ outcome, data: { redemptionId: "synthetic-redemption-result", points: 120, newBalance: 320, publicHint: "••••-DEMO", redeemedAtMs: 1_800_000_000_000, ledgerEntry: { id: "synthetic-redemption-ledger", userId: "prototype-user", kind: "redemption_credit", points: 120, createdAtMs: 1_800_000_000_000, referenceId: "synthetic-redemption-result", description: "兑换码 ••••-DEMO 到账" } } });

const open = (ledger?: PointsLedgerEntry[], officialOrders?: OfficialCheckoutOrder[]) => { const base = structuredClone(syntheticState); const state = { ...base, billing: { ...base.billing, ...(ledger ? { ledger } : {}), ...(officialOrders ? { officialOrders } : {}) } }; window.history.pushState({}, "", "/app/billing"); return render(<App initialAuthenticated initialState={state} />); };
const inputCode = (value = "SYNTHETIC-DEMO") => fireEvent.change(screen.getByLabelText("积分兑换码"), { target: { value } });

const ledgerRows = (count: number): PointsLedgerEntry[] => Array.from({ length: count }, (_, index) => ({
  id: `ledger-${index}`,
  userId: "prototype-user",
  kind: "purchase_credit",
  points: 100 + index,
  createdAtMs: 1_800_000_000_000 - index * 1_000,
  referenceId: `order-${index}`,
  description: `积分记录 ${index + 1}`,
}));

afterEach(() => vi.restoreAllMocks());

describe("billing points redemption", () => {
  it("groups repeated consumption by business category without changing source ledger rows", () => {
    const ledger: PointsLedgerEntry[] = [
      { id: "answer-2", userId: "prototype-user", kind: "usage_settle", points: -5, createdAtMs: 30, referenceId: "answer-2", description: "面试回答积分结算" },
      { id: "screenshot-1", userId: "prototype-user", kind: "usage_settle", points: -15, createdAtMs: 20, referenceId: "screenshot-1", description: "截图回答积分结算" },
      { id: "answer-1", userId: "prototype-user", kind: "usage_settle", points: -5, createdAtMs: 10, referenceId: "answer-1", description: "面试回答积分结算" },
      { id: "welcome", userId: "prototype-user", kind: "welcome_grant", points: 200, createdAtMs: 1, referenceId: "welcome", description: "新用户赠送积分" },
    ];

    const display = summarizePointsLedger(ledger);

    expect(ledger).toHaveLength(4);
    expect(display).toHaveLength(3);
    expect(display).toEqual(expect.arrayContaining([
      expect.objectContaining({ description: "普通回答消费", count: 2, points: -10 }),
      expect.objectContaining({ description: "截图回答消费", count: 1, points: -15 }),
      expect.objectContaining({ description: "新用户赠送积分", count: 1, points: 200 }),
    ]));
  });

  it("shows a repeated ledger reference once while preserving separate equal-value credits", () => {
    const ledger: PointsLedgerEntry[] = [
      { id: "welcome-copy-1", userId: "prototype-user", kind: "welcome_grant", points: 200, createdAtMs: 20, referenceId: "welcome:prototype-user", description: "新用户赠送积分" },
      { id: "welcome-copy-2", userId: "prototype-user", kind: "welcome_grant", points: 200, createdAtMs: 20, referenceId: "welcome:prototype-user", description: "新用户赠送积分" },
      { id: "redemption-separate", userId: "prototype-user", kind: "redemption_credit", points: 200, createdAtMs: 10, referenceId: "redemption:separate", description: "兑换码积分入账" },
    ];

    const display = summarizePointsLedger(ledger);

    expect(display).toHaveLength(2);
    expect(display.map((item) => item.id)).toEqual(["welcome-copy-1", "redemption-separate"]);
  });

  it("reports the unique backend ledger count when duplicate references are received", () => {
    const duplicate = { id: "welcome-copy-1", userId: "prototype-user", kind: "welcome_grant", points: 200, createdAtMs: 20, referenceId: "welcome:prototype-user", description: "新用户赠送积分" } satisfies PointsLedgerEntry;
    open([duplicate, { ...duplicate, id: "welcome-copy-2" }]);

    expect(screen.getByText("1 项 · 1 笔流水")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "积分明细记录" }).querySelectorAll("article")).toHaveLength(1);
  });

  it("starts empty with an accessible disabled action and no checkout", () => {
    open(); expect(screen.getByRole("button", { name: "立即兑换" })).toBeDisabled(); expect(screen.getByText(/输入 16 位兑换码/)).toBeInTheDocument(); expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("keeps support contacts and an empty official order state compact and accessible", () => {
    open();
    expect(screen.getByRole("heading", { name: "支付保障与售后" })).toBeInTheDocument();
    expect(screen.getByText("暂无成功订单")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "复制微信号" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "发送邮件" })).toHaveAttribute("href", "mailto:contact@oneshowailab.com");
  });

  it("shows only paid official orders in order history", () => {
    const product = syntheticState.billing.catalog[0]!;
    const order = (id: string, status: OfficialCheckoutOrder["status"]): OfficialCheckoutOrder => ({
      id,
      userId: "prototype-user",
      product,
      amountCents: product.priceCents,
      currency: "CNY",
      channel: "alipay",
      provider: "alipay",
      status,
      action: { kind: "redirect", url: "https://example.invalid/pay", expiresAtMs: 1_800_000_000_000 },
      createdAtMs: 1_700_000_000_000,
      updatedAtMs: 1_700_000_000_000,
    });
    open(undefined, [
      order("paid-order", "paid"),
      order("pending-order", "payment_pending"),
      order("failed-order", "failed"),
      order("closed-order", "closed"),
      order("refunded-order", "refunded"),
    ]);

    const history = screen.getByRole("heading", { name: "官方订单" }).closest("section")!;
    expect(within(history).getByText("1 笔")).toBeInTheDocument();
    expect(within(history).getByText(/paid-order/)).toBeInTheDocument();
    expect(within(history).queryByText(/pending-order|failed-order|closed-order|refunded-order/)).not.toBeInTheDocument();
  });

  it("keeps every ledger row in a named, keyboard-scrollable five-row viewport", () => {
    open(ledgerRows(8));
    const ledger = screen.getByRole("region", { name: "积分明细记录" });
    expect(ledger).toHaveClass("points-ledger-scroll");
    expect(ledger).toHaveAttribute("tabindex", "0");
    const styles = readFileSync("src/styles.css", "utf8");
    expect(styles).toMatch(/\.points-ledger-scroll\s*\{[^}]*max-height:\s*225px;[^}]*overflow-y:\s*auto;/s);
    expect(ledger.querySelectorAll("article")).toHaveLength(8);
    expect(within(ledger).getAllByText(/积分记录/).map(node => node.textContent)).toEqual([
      "积分记录 1", "积分记录 2", "积分记录 3", "积分记录 4", "积分记录 5", "积分记录 6", "积分记录 7", "积分记录 8",
    ]);
    expect(document.querySelector(".billing-orders-panel .points-ledger-scroll")).not.toBeInTheDocument();
  });

  it("shows five or fewer rows without adding an unnecessary keyboard stop on a small screen", () => {
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 390 });
    open(ledgerRows(5));
    const ledger = screen.getByRole("region", { name: "积分明细记录" });
    expect(ledger).not.toHaveAttribute("tabindex");
    expect(ledger.querySelectorAll("article")).toHaveLength(5);
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

  it("does not append a redemption ledger row already present by its server reference", async () => {
    const result = success();
    if (!("data" in result)) throw new Error("synthetic redemption result must include data");
    const existing = result.data.ledgerEntry;
    vi.spyOn(interviewAppAdapter, "redeemPoints").mockResolvedValue(result);
    open([existing]);
    inputCode();
    fireEvent.click(screen.getByRole("button", { name: "立即兑换" }));

    await screen.findByText(/兑换成功：\+120 点/);
    expect(screen.getByRole("region", { name: "积分明细记录" }).querySelectorAll("article")).toHaveLength(1);
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
