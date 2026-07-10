import { describe, expect, it } from "vitest";
import { BillingError, BillingService, defaultBillingProducts } from "../src/billing-service.js";
import { knowledgeEconomicsFixtures } from "./fixtures/knowledge-economics.js";

describe("BillingService", () => {
  it("grants welcome points exactly once", () => {
    const service = new BillingService();
    service.grantWelcome("u1", true, 1); service.grantWelcome("u1", true, 2);
    expect(service.balance("u1")).toBe(200);
    expect(service.entries("u1").filter(entry => entry.kind === "welcome_grant")).toHaveLength(1);
  });

  it("reserves and settles answer and screenshot rates idempotently", () => {
    const service = new BillingService(); service.grantWelcome("u1", true);
    service.reserveUsage("u1", "answer-1", "answer"); service.reserveUsage("u1", "answer-1", "answer");
    expect(service.balance("u1")).toBe(195); service.settleUsage("answer-1"); service.settleUsage("answer-1");
    service.reserveUsage("u1", "shot-1", "screenshot_answer"); service.settleUsage("shot-1");
    expect(service.balance("u1")).toBe(180);
  });

  it("releases points on failed work", () => {
    const service = new BillingService(); service.grantWelcome("u1", true); service.reserveUsage("u1", "failed", "screenshot_answer");
    service.releaseUsage("failed"); expect(service.balance("u1")).toBe(200);
  });

  it("activates a manual order once and enforces reviewer roles", () => {
    const service = new BillingService(); const order = service.createOrder("u1", "points-300", "wechat", 1);
    service.submitProof("u1", order.id, "proof-a", "wx-transaction-a");
    expect(() => service.reviewOrder("support", order.id, true)).toThrowError(expect.objectContaining({ code: "forbidden" }));
    service.reviewOrder("payment-reviewer", order.id, true, 2); service.reviewOrder("payment-reviewer", order.id, true, 3);
    expect(service.balance("u1")).toBe(300);
  });

  it("detects duplicate proof and wrong-user order access", () => {
    const service = new BillingService(); const first = service.createOrder("u1", "points-300", "wechat"); const second = service.createOrder("u1", "points-800", "alipay");
    service.submitProof("u1", first.id, "same-proof", "tx1");
    expect(() => service.submitProof("u1", second.id, "same-proof", "tx2")).toThrowError(expect.objectContaining({ code: "duplicate-proof" }));
    expect(() => service.submitProof("u2", second.id, "proof-b", "tx2")).toThrowError(expect.objectContaining({ code: "forbidden" }));
  });

  it("extends passes and gives them precedence over points", () => {
    const service = new BillingService(); service.grantWelcome("u1", true, 1);
    const first = service.createOrder("u1", "pass-3", "wechat", 10); service.submitProof("u1", first.id, "p1", "t1"); service.reviewOrder("payment-reviewer", first.id, true, 100);
    const second = service.createOrder("u1", "pass-7", "wechat", 110); service.submitProof("u1", second.id, "p2", "t2"); service.reviewOrder("payment-reviewer", second.id, true, 120);
    const passes = service.entitlements("u1"); expect(passes[1]!.startsAtMs).toBe(passes[0]!.endsAtMs); expect(passes[1]!.endsAtMs - passes[1]!.startsAtMs).toBe(7 * 86_400_000);
    const usage = service.reserveUsage("u1", "member-answer", "answer", 130); expect(usage.source).toBe("time_pass"); expect(service.balance("u1")).toBe(200);
  });

  it("rejects insufficient balances and unprofitable catalog publication", () => {
    const service = new BillingService(); expect(() => service.reserveUsage("u1", "answer", "answer")).toThrow(BillingError);
    expect(() => service.publish({ ...defaultBillingProducts[0]!, id: "bad" }, .2)).toThrowError(expect.objectContaining({ code: "unprofitable" }));
  });

  it("publishes revised knowledge allowances and keeps short-pass indexing point-billed", () => {
    const service = new BillingService();
    expect(service.catalog().map(item => item.priceCents)).toEqual([6990, 12990, 21990, 32990, 3990, 8990, 19990]);
    service.grantWelcome("u1", true, 1); const order = service.createOrder("u1", "pass-3", "wechat", 2); service.submitProof("u1", order.id, "member-proof", "member-tx"); service.reviewOrder("payment-reviewer", order.id, true, 3);
    const usage = service.reserveUsage("u1", "knowledge-1", "knowledge_index", 4, "document-v1", 200); expect(usage).toMatchObject({ source: "points", points: 200, documentVersionId: "document-v1" }); expect(service.balance("u1")).toBe(0);
  });

  it("locks, settles and releases two long-pass knowledge allowances", () => {
    const service = new BillingService(); service.grantWelcome("u1", true, 1); const order = service.createOrder("u1", "pass-15", "wechat", 2); service.submitProof("u1", order.id, "long-proof", "long-tx"); service.reviewOrder("payment-reviewer", order.id, true, 3);
    expect(service.knowledgeAllowance("u1", 4)?.remaining).toBe(2);
    const first = service.reserveUsage("u1", "k1", "knowledge_index", 4, "d1", 200); expect(first.source).toBe("pass_allowance"); expect(service.knowledgeAllowance("u1", 4)?.remaining).toBe(1);
    service.releaseUsage("k1", 5); expect(service.knowledgeAllowance("u1", 5)?.remaining).toBe(2);
    service.reserveUsage("u1", "k2", "knowledge_index", 6, "d2", 200); service.settleUsage("k2", 7); expect(service.knowledgeAllowance("u1", 7)?.remaining).toBe(1); expect(service.balance("u1")).toBe(200);
  });

  it("does not expose a queued long-pass allowance before its segment starts", () => {
    const service = new BillingService(); const short = service.createOrder("u1", "pass-3", "wechat", 1); service.submitProof("u1", short.id, "short", "short-tx"); service.reviewOrder("payment-reviewer", short.id, true, 10);
    const long = service.createOrder("u1", "pass-15", "wechat", 11); service.submitProof("u1", long.id, "long", "long-tx"); service.reviewOrder("payment-reviewer", long.id, true, 12);
    const passes = service.entitlements("u1"); expect(service.knowledgeAllowance("u1", 13)?.remaining).toBe(0); expect(service.knowledgeAllowance("u1", passes[1]!.startsAtMs)?.remaining).toBe(2); expect(service.knowledgeAllowance("u1", passes[1]!.endsAtMs)).toBeNull();
  });

  it("keeps synthetic knowledge and long-pass economics above the publication margin", () => {
    for (const item of knowledgeEconomicsFixtures.knowledgeCases) { const revenue = item.chargedPoints * knowledgeEconomicsFixtures.pointValueCents; expect((revenue - item.estimatedCostCents) / revenue).toBeGreaterThanOrEqual(knowledgeEconomicsFixtures.minimumGrossMargin); }
    for (const item of knowledgeEconomicsFixtures.longPassCases) expect((item.priceCents - item.conservativeTotalCostCents) / item.priceCents).toBeGreaterThanOrEqual(knowledgeEconomicsFixtures.minimumGrossMargin);
  });
});
