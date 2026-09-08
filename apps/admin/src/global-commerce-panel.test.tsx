// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { GlobalCommercePanel } from "./App";


describe("GlobalCommercePanel", () => {
  it("shows customer-facing paid plans instead of internal offer codes", () => {
    render(<GlobalCommercePanel row={{
      mode: "test",
      runtimeMode: "test",
      masterSwitchEnabled: true,
      providerActivated: false,
      configurationReady: false,
      blockers: ["Creem API Key 未配置"],
      credentials: { apiKey: { configured: false }, webhookSecret: { configured: false } },
      urls: { webhookUrl: "https://offersteady.com/api/v1/global-commerce/webhooks/creem" },
      mappings: [
        { offerCode: "global-interview-pass", displayName: "Interview Day Pass", priceCents: 999, currency: "USD", billingMode: "one_time", validationStatus: "missing" },
        { offerCode: "global-pro-weekly", displayName: "Pro Weekly", priceCents: 4999, currency: "USD", billingMode: "one_time", validationStatus: "missing" },
        { offerCode: "global-pro-monthly", displayName: "Pro Monthly", priceCents: 9999, currency: "USD", billingMode: "recurring", validationStatus: "missing" },
        { offerCode: "global-job-hunt", displayName: "Job Hunt", priceCents: 19999, currency: "USD", billingMode: "one_time", validationStatus: "missing" },
      ],
      metrics: {},
      operations: { orders: [], subscriptions: [], events: [] },
    }} onChanged={() => undefined} />);

    expect(screen.getByText("Interview Day Pass")).toBeTruthy();
    expect(screen.getByText("Pro Weekly")).toBeTruthy();
    expect(screen.getByText(/Free 是免费权益/)).toBeTruthy();
    expect(screen.queryByText("global-pro-weekly")).toBeNull();
    expect(screen.getByRole("button", { name: "启用 Test 测试支付" }).hasAttribute("disabled")).toBe(true);
  });
});
