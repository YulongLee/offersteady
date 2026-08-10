import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { OfficialCheckoutOrder, TimePassEntitlement } from "@offersteady/protocol";
import { App } from "./App";
import { interviewAppAdapter } from "./app-adapter";
import { formatMembershipDuration, formatMembershipRemaining } from "./BillingPage";
import { syntheticState } from "./test-state";

const baseNow = 1_800_000_000_000;
const dayMs = 86_400_000;
const hourMs = 3_600_000;

const entitlement = (overrides: Partial<TimePassEntitlement> = {}): TimePassEntitlement => ({
  id: "member-active",
  userId: syntheticState.account.id,
  productId: "pass-7",
  orderId: "order-active",
  startsAtMs: baseNow - dayMs,
  endsAtMs: baseNow + 6 * dayMs + 12 * hourMs,
  knowledgeAllowanceGranted: 2,
  knowledgeAllowanceUsed: 1,
  knowledgeAllowanceLocked: 0,
  ...overrides,
});

const open = (mutate?: (state: typeof syntheticState) => void) => {
  const state = structuredClone(syntheticState);
  mutate?.(state);
  window.history.pushState({}, "", "/app/billing");
  return render(<App initialAuthenticated initialState={state} />);
};

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("billing membership visibility", () => {
  it("formats remaining membership at day, hour, minute and expiry boundaries", () => {
    expect(formatMembershipRemaining(baseNow + 2 * dayMs + 3 * hourMs, baseNow)).toBe("2 天 3 小时");
    expect(formatMembershipRemaining(baseNow + 4 * hourMs + 25 * 60_000, baseNow)).toBe("4 小时 25 分钟");
    expect(formatMembershipRemaining(baseNow + 20_000, baseNow)).toBe("0 小时 1 分钟");
    expect(formatMembershipRemaining(baseNow, baseNow)).toBe("已到期");
    expect(formatMembershipDuration(15 * dayMs)).toBe("15 天 0 小时");
  });

  it("makes an active membership primary while retaining points and queued extensions", () => {
    vi.useFakeTimers();
    vi.setSystemTime(baseNow);
    open(state => {
      state.billing = {
        ...state.billing,
        activePass: entitlement(),
        queuedPasses: [entitlement({
          id: "member-queued",
          orderId: "order-queued",
          startsAtMs: baseNow + 6 * dayMs + 12 * hourMs,
          endsAtMs: baseNow + 21 * dayMs + 12 * hourMs,
        })],
      };
    });

    const card = screen.getByRole("region", { name: "我的权益" });
    expect(within(card).getByText("会员使用中")).toBeInTheDocument();
    expect(within(card).getByText("剩余 6 天 12 小时")).toBeInTheDocument();
    expect(within(card).getByText("知识材料额度 1/2")).toBeInTheDocument();
    expect(within(card).getByText("200 点")).toBeInTheDocument();
    expect(screen.getByText(/1 个 · 共 15 天 0 小时/)).toBeInTheDocument();
    expect(screen.getAllByText("积分与会员").length).toBeGreaterThan(0);
  });

  it("shows the explicit no-membership state and switches safely at expiry", async () => {
    vi.useFakeTimers();
    vi.setSystemTime(baseNow);
    const refreshed = { ...structuredClone(syntheticState.billing), activePass: null, queuedPasses: [] };
    vi.spyOn(interviewAppAdapter, "getBillingState").mockResolvedValue(refreshed);
    open(state => { state.billing = { ...state.billing, activePass: entitlement({ endsAtMs: baseNow + 60_000 }) }; });
    expect(screen.getByText("会员使用中")).toBeInTheDocument();

    await act(async () => { await vi.advanceTimersByTimeAsync(60_100); });

    expect(screen.getByText("当前未开通会员")).toBeInTheDocument();
    expect(screen.getByText("200 点", { selector: ".balance-card strong" })).toBeInTheDocument();
  });

  it("reloads trusted entitlements after a paid time-pass order", async () => {
    vi.useFakeTimers();
    vi.setSystemTime(baseNow);
    const product = syntheticState.billing.catalog.find(item => item.id === "pass-1")!;
    const pending: OfficialCheckoutOrder = {
      id: "checkout-membership",
      userId: syntheticState.account.id,
      product,
      amountCents: product.priceCents,
      currency: "CNY",
      channel: "alipay",
      provider: "alipay",
      status: "payment_pending",
      action: { kind: "redirect", url: "https://openapi.alipay.com/gateway.do?synthetic=1", expiresAtMs: baseNow + 15 * 60_000 },
      createdAtMs: baseNow,
      updatedAtMs: baseNow,
    };
    const paid: OfficialCheckoutOrder = { ...pending, status: "paid", updatedAtMs: baseNow + 3_000 };
    const refreshed = { ...structuredClone(syntheticState.billing), activePass: entitlement({ productId: "pass-1", orderId: pending.id, startsAtMs: baseNow, endsAtMs: baseNow + dayMs }) };
    vi.spyOn(window, "open").mockReturnValue(null);
    vi.spyOn(interviewAppAdapter, "createCheckoutOrder").mockResolvedValue(pending);
    vi.spyOn(interviewAppAdapter, "getCheckoutOrder").mockResolvedValue(paid);
    const getBillingState = vi.spyOn(interviewAppAdapter, "getBillingState").mockResolvedValue(refreshed);
    open();

    const productCard = screen.getByRole("heading", { name: "1 天会员" }).closest("article")!;
    fireEvent.click(within(productCard).getByRole("button", { name: "购买" }));
    fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "支付宝支付" }));
    await act(async () => { await Promise.resolve(); await Promise.resolve(); });
    await act(async () => { await vi.advanceTimersByTimeAsync(3_000); await Promise.resolve(); });

    expect(getBillingState).toHaveBeenCalledOnce();
    expect(screen.getByText("会员使用中")).toBeInTheDocument();
    expect(screen.getByText("剩余 1 天 0 小时")).toBeInTheDocument();
    expect(screen.getByText("支付已由服务端验签确认，权益已到账")).toBeInTheDocument();
  });
});
