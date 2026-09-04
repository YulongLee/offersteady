// @vitest-environment jsdom

import { renderToStaticMarkup } from "react-dom/server";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { afterEach, describe, expect, it, vi } from "vitest";

import { PromotionCenter } from "./PromotionCenter";
import { adminApi } from "./api";

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

const stubOverviewRequests = () => {
  vi.spyOn(adminApi, "promotionOverview").mockResolvedValue({ metrics: {}, metadata: { freshness: "current", cohortState: "observing" } });
  vi.spyOn(adminApi, "promotionTrends").mockResolvedValue({ items: [], metadata: {} });
  vi.spyOn(adminApi, "promotionFunnel").mockResolvedValue({ stages: [], cohortState: "observing" });
  vi.spyOn(adminApi, "promotionReport").mockResolvedValue({ items: [], metadata: {} });
  vi.spyOn(adminApi, "promotionHealth").mockResolvedValue({ queue: { state: "healthy", pending: 0, dropped: 0 } });
};

const stubPartnerRequests = () => {
  vi.spyOn(adminApi, "partnerReconciliation").mockResolvedValue({ pendingCents: 100, availableCents: 200, reservedCents: 300, paidCents: 400, reversedCents: 50, negativeCarryCents: 0 });
  vi.spyOn(adminApi, "partnerCommissionOrders").mockResolvedValue({ items: [] });
};

describe("promotion center shell", () => {
  it("exposes all operator tasks and accessible report filters", () => {
    const html = renderToStaticMarkup(<PromotionCenter permissions={["promotion.read"]} onAuthenticationExpired={() => undefined} />);
    expect(html).toContain("推广总览");
    expect(html).toContain("推广链接");
    expect(html).toContain("营销活动");
    expect(html).toContain("渠道分析");
    expect(html).toContain("转化漏斗");
    expect(html).toContain("合作伙伴");
    expect(html).toContain('aria-label="统计周期"');
    expect(html).toContain('aria-label="归因模型"');
    expect(html).toContain('role="tab"');
    expect(html).toContain('aria-selected="true"');
  });

  it("does not expose mutation forms to a read-only operator", () => {
    const html = renderToStaticMarkup(<PromotionCenter permissions={["promotion.read"]} onAuthenticationExpired={() => undefined} />);
    expect(html).not.toContain("追加推广成本");
    expect(html).not.toContain("新建渠道");
  });

  it("announces loading, empty and freshness states without rendering missing values as data", async () => {
    stubOverviewRequests();
    render(<PromotionCenter permissions={["promotion.read"]} onAuthenticationExpired={() => undefined} />);
    expect(screen.getByText("正在读取推广数据…")).toBeTruthy();
    await waitFor(() => expect(screen.getByText(/日快照尚未生成/)).toBeTruthy());
    expect(screen.getByText("数据状态：数据已更新")).toBeTruthy();
    expect(screen.getByText("人群观察：观察中")).toBeTruthy();
  });

  it("offers a keyboard-focusable retry after a report error", async () => {
    stubOverviewRequests();
    vi.mocked(adminApi.promotionOverview).mockRejectedValueOnce(new Error("推广快照暂时不可用"));
    render(<PromotionCenter permissions={["promotion.read"]} onAuthenticationExpired={() => undefined} />);
    const retry = await screen.findByRole("button", { name: "重试" });
    expect(retry.tagName).toBe("BUTTON");
    fireEvent.click(retry);
    await waitFor(() => expect(screen.queryByRole("button", { name: "重试" })).toBeNull());
  });

  it("renders delayed freshness explicitly instead of converting it to zero", async () => {
    stubOverviewRequests();
    vi.mocked(adminApi.promotionOverview).mockResolvedValueOnce({ metrics: { costCents: null }, metadata: { freshness: "delayed", cohortState: "observing" } });
    render(<PromotionCenter permissions={["promotion.read"]} onAuthenticationExpired={() => undefined} />);
    await waitFor(() => expect(screen.getByText("数据状态：数据延迟")).toBeTruthy());
    expect(screen.getAllByText("成本未录入").length).toBeGreaterThan(0);
  });

  it("renders promotion indicators and states in Chinese instead of raw API keys", async () => {
    stubOverviewRequests();
    vi.spyOn(adminApi, "promotionChannels").mockResolvedValue({ items: [{ channelId: "channel-one", code: "nowcoder", name: "牛客", status: "active", isSystem: false }] });
    vi.spyOn(adminApi, "promotionCampaigns").mockResolvedValue({ items: [] });
    vi.spyOn(adminApi, "promotionLinks").mockResolvedValue({ items: [] });
    render(<PromotionCenter permissions={["promotion.read"]} onAuthenticationExpired={() => undefined} />);
    await waitFor(() => expect(screen.getByText(/日快照尚未生成/)).toBeTruthy());
    vi.mocked(adminApi.promotionReport).mockResolvedValueOnce({ items: [{ dimensionId: "channel-one", dimensionName: "牛客", uniqueVisitors: 3, registrationRate: 0.5, revenueCents: 9900 }], metadata: {} });
    fireEvent.click(screen.getByRole("tab", { name: "渠道分析" }));
    await waitFor(() => expect(screen.getByText("有效访客")).toBeTruthy());
    expect(screen.getByText("系统渠道")).toBeTruthy();
    expect(screen.getByText("已启用")).toBeTruthy();
    expect(screen.queryByText("uniqueVisitors")).toBeNull();
    expect(screen.queryByText("registrationRate")).toBeNull();
  });

  it("keeps empty link management truthful and keyboard reachable", async () => {
    vi.spyOn(adminApi, "promotionChannels").mockResolvedValue({ items: [] });
    vi.spyOn(adminApi, "promotionCampaigns").mockResolvedValue({ items: [] });
    vi.spyOn(adminApi, "promotionLinks").mockResolvedValue({ items: [] });
    stubOverviewRequests();
    render(<PromotionCenter permissions={["promotion.read"]} onAuthenticationExpired={() => undefined} />);
    const linksTab = screen.getByRole("tab", { name: "推广链接" });
    linksTab.focus();
    expect(document.activeElement).toBe(linksTab);
    fireEvent.click(linksTab);
    await waitFor(() => expect(screen.getByText(/还没有推广链接/)).toBeTruthy());
  });

  it("has bounded responsive layouts for tablet and mobile widths", () => {
    const css = readFileSync("src/styles.css", "utf8");
    expect(css).toContain("@media (max-width: 900px)");
    expect(css).toContain("@media (max-width: 560px)");
    expect(css).toMatch(/@media \(max-width: 560px\)[\s\S]*?\.promotion-kpis[\s\S]*?grid-template-columns:\s*1fr/);
  });

  it("renders all five management pages from one synthetic closed-loop dataset", async () => {
    stubOverviewRequests();
    vi.mocked(adminApi.promotionFunnel).mockResolvedValue({
      stages: [{ key: "visit", label: "有效访问", count: 2, stageRate: 1, cumulativeRate: 1, dropOff: 0 }],
      cohortState: "observing",
    });
    vi.spyOn(adminApi, "promotionChannels").mockResolvedValue({ items: [{ channelId: "channel-nowcoder", code: "nowcoder", name: "牛客", status: "active", isSystem: false }] });
    vi.spyOn(adminApi, "promotionCampaigns").mockResolvedValue({ items: [{ campaignId: "campaign-autumn", name: "2026 秋招推广", status: "active", channelCount: 1, linkCount: 1 }] });
    vi.spyOn(adminApi, "promotionLinks").mockResolvedValue({ items: [{ linkId: "link-article", contentName: "牛客算法经验帖", channelId: "channel-nowcoder", channelName: "牛客", campaignId: "campaign-autumn", campaignName: "2026 秋招推广", destinationPath: "/", publicUrl: "https://example.test/r/AbCd123456", status: "active" }] });

    render(<PromotionCenter permissions={["promotion.read"]} onAuthenticationExpired={() => undefined} />);
    await waitFor(() => expect(screen.getByText(/日快照尚未生成/)).toBeTruthy());
    fireEvent.click(screen.getByRole("tab", { name: "推广链接" }));
    await waitFor(() => expect(screen.getByText("牛客算法经验帖")).toBeTruthy());
    fireEvent.click(screen.getByRole("tab", { name: "营销活动" }));
    await waitFor(() => expect(screen.getByText("2026 秋招推广")).toBeTruthy());
    fireEvent.click(screen.getByRole("tab", { name: "渠道分析" }));
    await waitFor(() => expect(screen.getAllByText("牛客").length).toBeGreaterThan(0));
    fireEvent.click(screen.getByRole("tab", { name: "转化漏斗" }));
    await waitFor(() => expect(screen.getByText("有效访问")).toBeTruthy());
  });

  it("shows aggregate partners and permission-gated payout actions", async () => {
    stubOverviewRequests();
    stubPartnerRequests();
    vi.spyOn(adminApi, "promotionPartners").mockResolvedValue({ items: [{ profileId: "partner-safe", status: "active", joinedAtMs: 1, totalCommissionCents: 2000 }] });
    vi.spyOn(adminApi, "partnerPayouts").mockResolvedValue({ items: [{ payoutRequestId: "payout-safe", periodKey: "2026-09", amountCents: 12000, status: "requested", requestedAtMs: 1 }] });
    render(<PromotionCenter permissions={["promotion.read", "promotion.payout.manage"]} onAuthenticationExpired={() => undefined} />);
    fireEvent.click(screen.getByRole("tab", { name: "合作伙伴" }));
    await waitFor(() => expect(screen.getByText("待审核结算：1")).toBeTruthy());
    expect(screen.getByRole("button", { name: "同步已支付订单佣金" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "批准" })).toBeTruthy();
    expect(document.body.textContent).not.toContain("phone");
  });

  it("records a partner refund with an integer-cent channel reference", async () => {
    stubOverviewRequests();
    stubPartnerRequests();
    vi.spyOn(adminApi, "promotionPartners").mockResolvedValue({ items: [] });
    vi.spyOn(adminApi, "partnerPayouts").mockResolvedValue({ items: [] });
    const record = vi.spyOn(adminApi, "recordPartnerRefund").mockResolvedValue({});
    render(<PromotionCenter permissions={["promotion.read", "promotion.payout.manage"]} onAuthenticationExpired={() => undefined} />);
    fireEvent.click(screen.getByRole("tab", { name: "合作伙伴" }));
    await screen.findByText("退款佣金冲正");
    fireEvent.change(screen.getByPlaceholderText("原支付订单号"), { target: { value: "order-001" } });
    fireEvent.change(screen.getByPlaceholderText("渠道退款单号（幂等凭证）"), { target: { value: "refund-001" } });
    fireEvent.change(screen.getByPlaceholderText("退款金额（元）"), { target: { value: "12.34" } });
    fireEvent.change(screen.getByPlaceholderText("冲正原因"), { target: { value: "渠道退款已确认" } });
    fireEvent.click(screen.getByRole("button", { name: "记录退款冲正" }));
    await waitFor(() => expect(record).toHaveBeenCalledWith({
      orderId: "order-001", refundReference: "refund-001", refundedCents: 1234, reason: "渠道退款已确认",
    }));
  });


  it("reveals one masked payout only to payout managers after explicit confirmation", async () => {
    stubOverviewRequests(); stubPartnerRequests();
    vi.spyOn(adminApi, "promotionPartners").mockResolvedValue({ items: [] });
    vi.spyOn(adminApi, "partnerPayouts").mockResolvedValue({ items: [{ payoutRequestId: "payout-safe", periodKey: "2026-09", amountCents: 12000, status: "approved", payoutMethod: "alipay", maskedAccountName: "测*", maskedAccountIdentifier: "****1234" }] });
    const reveal = vi.spyOn(adminApi, "revealPartnerPayout").mockResolvedValue({ payoutMethod: "alipay", accountName: "测试用户", accountIdentifier: "account-1234" });
    vi.spyOn(window, "confirm").mockReturnValue(true);
    render(<PromotionCenter permissions={["promotion.read", "promotion.payout.manage"]} onAuthenticationExpired={() => undefined} />);
    fireEvent.click(screen.getByRole("tab", { name: "合作伙伴" }));
    const button = await screen.findByRole("button", { name: "查看本单收款信息" });
    fireEvent.click(button);
    await waitFor(() => expect(reveal).toHaveBeenCalledWith("payout-safe"));
    expect(await screen.findByText("账号：account-1234")).toBeTruthy();
  });
});
