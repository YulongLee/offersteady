import type { BillableOperationKind, BillingOrder, BillingProduct, BillingSupportConfig, LedgerEntryKind, PaymentChannel, PointsLedgerEntry, TimePassEntitlement, UsageCharge, UsageRates } from "@offersteady/protocol";

const DAY_MS = 86_400_000;
export const defaultUsageRates: UsageRates = { catalogVersion: 3, answerPoints: 5, screenshotAnswerPoints: 15, knowledgeIndexMinimumPoints: 200, knowledgeIndexPointsPer1000Tokens: 20, tokenizerVersion: "synthetic-v1" };
export const defaultBillingProducts: readonly BillingProduct[] = [
  { id: "pass-3", catalogVersion: 3, kind: "time_pass", displayName: "3 天会员", priceCents: 6990, durationDays: 3, knowledgeIndexAllowance: 0, published: true },
  { id: "pass-7", catalogVersion: 3, kind: "time_pass", displayName: "7 天会员", priceCents: 12990, durationDays: 7, knowledgeIndexAllowance: 0, published: true },
  { id: "pass-15", catalogVersion: 3, kind: "time_pass", displayName: "15 天会员", priceCents: 21990, durationDays: 15, knowledgeIndexAllowance: 2, published: true },
  { id: "pass-30", catalogVersion: 3, kind: "time_pass", displayName: "30 天会员", priceCents: 32990, durationDays: 30, knowledgeIndexAllowance: 2, published: true },
  { id: "points-300", catalogVersion: 3, kind: "points_pack", displayName: "300 点", priceCents: 3990, points: 300, published: true },
  { id: "points-800", catalogVersion: 3, kind: "points_pack", displayName: "800 点", priceCents: 8990, points: 800, published: true },
  { id: "points-2000", catalogVersion: 3, kind: "points_pack", displayName: "2000 点", priceCents: 19990, points: 2000, published: true },
];

export interface PaymentProviderAdapter {
  createPayment(order: BillingOrder): Promise<{ paymentUrl: string }>;
  queryPayment(orderId: string): Promise<"pending" | "paid" | "failed">;
  refund(orderId: string): Promise<"refunded" | "failed">;
}

export class BillingError extends Error {
  constructor(readonly code: "not-found" | "insufficient-balance" | "forbidden" | "invalid-state" | "duplicate-proof" | "unprofitable", message: string) { super(message); }
}

export class BillingService {
  private products = new Map<string, BillingProduct>();
  private ledger = new Map<string, PointsLedgerEntry[]>();
  private welcomeGranted = new Set<string>();
  private passes = new Map<string, TimePassEntitlement[]>();
  private usages = new Map<string, UsageCharge>();
  private orders = new Map<string, BillingOrder>();
  private activatedOrders = new Set<string>();
  private proofFingerprints = new Set<string>();
  private counter = 0;

  constructor(products: readonly BillingProduct[] = defaultBillingProducts, readonly rates: UsageRates = defaultUsageRates, readonly support: BillingSupportConfig = { wechatId: "offersteady_support", qrAssetPath: "/support/wechat-placeholder.png", serviceHours: "工作日 10:00–18:00", refundSummary: "退款按订单状态和未使用权益人工审核" }) { products.forEach(product => this.products.set(product.id, product)); }

  catalog() { return [...this.products.values()].filter(product => product.published); }
  publish(product: BillingProduct, projectedMargin: number, minimumMargin = .6) {
    this.validateProduct(product);
    if (projectedMargin < minimumMargin) throw new BillingError("unprofitable", "预计毛利低于发布阈值");
    this.products.set(product.id, { ...product, published: true });
  }
  unpublish(productId: string) { const product = this.product(productId); this.products.set(productId, { ...product, published: false }); }

  grantWelcome(userId: string, verified: boolean, nowMs = Date.now()) {
    if (!verified) throw new BillingError("forbidden", "账号尚未完成验证");
    if (this.welcomeGranted.has(userId)) return this.entries(userId).find(entry => entry.kind === "welcome_grant")!;
    this.welcomeGranted.add(userId); return this.addEntry(userId, "welcome_grant", 200, `welcome:${userId}`, "新用户测试积分", nowMs);
  }

  entries(userId: string) { return [...(this.ledger.get(userId) ?? [])]; }
  entitlements(userId: string) { return [...(this.passes.get(userId) ?? [])]; }
  balance(userId: string) { return this.entries(userId).reduce((total, entry) => total + entry.points, 0); }
  creditRedemption(userId: string, redemptionId: string, points: number, publicHint: string, nowMs = Date.now()) {
    if (!Number.isInteger(points) || points <= 0) throw new BillingError("invalid-state", "兑换积分必须是正整数");
    return this.addEntry(userId, "redemption_credit", points, redemptionId, `兑换码 ${publicHint} 到账`, nowMs);
  }
  reverseRedemption(userId: string, redemptionId: string, points: number, nowMs = Date.now()) {
    if (!Number.isInteger(points) || points <= 0 || this.balance(userId) < points) throw new BillingError("insufficient-balance", "余额不足，不能自动冲正");
    return this.addEntry(userId, "redemption_reversal", -points, redemptionId, "兑换积分冲正", nowMs);
  }
  activePass(userId: string, nowMs = Date.now()) { return (this.passes.get(userId) ?? []).filter(pass => pass.startsAtMs <= nowMs && pass.endsAtMs > nowMs).sort((a, b) => b.endsAtMs - a.endsAtMs)[0] ?? null; }
  knowledgeAllowance(userId: string, nowMs = Date.now()) { const pass = this.activePass(userId, nowMs); return pass ? { entitlementId: pass.id, remaining: Math.max(0, pass.knowledgeAllowanceGranted - pass.knowledgeAllowanceUsed - pass.knowledgeAllowanceLocked), expiresAtMs: pass.endsAtMs } : null; }

  reserveUsage(userId: string, usageId: string, kind: BillableOperationKind, nowMs = Date.now(), documentVersionId?: string, pointsOverride?: number, quote?: { quoteId: string; tokenCount: number; tokenizerVersion: string }): UsageCharge {
    const existing = this.usages.get(usageId); if (existing) return existing;
    const pass = this.activePass(userId, nowMs);
    const points = pointsOverride ?? (kind === "answer" ? this.rates.answerPoints : kind === "screenshot_answer" ? this.rates.screenshotAnswerPoints : this.rates.knowledgeIndexMinimumPoints);
    if (pass && kind !== "knowledge_index") { const charge: UsageCharge = { usageId, userId, kind, points: 0, source: "time_pass", status: "reserved", catalogVersion: this.rates.catalogVersion }; this.usages.set(usageId, charge); return charge; }
    const allowance = kind === "knowledge_index" ? this.knowledgeAllowance(userId, nowMs) : null;
    if (allowance && allowance.remaining > 0) {
      this.updatePass(allowance.entitlementId, value => ({ ...value, knowledgeAllowanceLocked: value.knowledgeAllowanceLocked + 1 }));
      const charge: UsageCharge = { usageId, userId, kind, points: 0, source: "pass_allowance", status: "reserved", catalogVersion: this.rates.catalogVersion, ...(documentVersionId ? { documentVersionId } : {}), entitlementId: allowance.entitlementId, ...(quote ? quote : {}) };
      this.usages.set(usageId, charge); return charge;
    }
    if (this.balance(userId) < points) throw new BillingError("insufficient-balance", "积分不足");
    const label = kind === "answer" ? "普通回答" : kind === "screenshot_answer" ? "截图回答" : "资料索引";
    this.addEntry(userId, "usage_reserve", -points, usageId, `${label}预留`, nowMs);
    const charge: UsageCharge = { usageId, userId, kind, points, source: "points", status: "reserved", catalogVersion: this.rates.catalogVersion, ...(documentVersionId ? { documentVersionId } : {}), ...(quote ? quote : {}) }; this.usages.set(usageId, charge); return charge;
  }

  settleUsage(usageId: string, nowMs = Date.now()) {
    const usage = this.usage(usageId); if (usage.status === "settled") return usage;
    if (usage.status !== "reserved") throw new BillingError("invalid-state", "用量无法结算");
    if (usage.source === "points") this.addEntry(usage.userId, "usage_settle", 0, usageId, "回答已成功交付", nowMs);
    if (usage.source === "pass_allowance" && usage.entitlementId) this.updatePass(usage.entitlementId, value => ({ ...value, knowledgeAllowanceLocked: Math.max(0, value.knowledgeAllowanceLocked - 1), knowledgeAllowanceUsed: value.knowledgeAllowanceUsed + 1 }));
    const settled: UsageCharge = { ...usage, status: "settled" }; this.usages.set(usageId, settled); return settled;
  }

  releaseUsage(usageId: string, nowMs = Date.now()) {
    const usage = this.usage(usageId); if (usage.status === "released") return usage;
    if (usage.status === "settled") throw new BillingError("invalid-state", "已结算用量不能释放");
    if (usage.source === "points") this.addEntry(usage.userId, "usage_release", usage.points, usageId, "任务未成功，积分已释放", nowMs);
    if (usage.source === "pass_allowance" && usage.entitlementId) this.updatePass(usage.entitlementId, value => ({ ...value, knowledgeAllowanceLocked: Math.max(0, value.knowledgeAllowanceLocked - 1) }));
    const released: UsageCharge = { ...usage, status: "released" }; this.usages.set(usageId, released); return released;
  }

  createOrder(userId: string, productId: string, channel: PaymentChannel, nowMs = Date.now()) {
    const product = this.product(productId); if (!product.published) throw new BillingError("invalid-state", "商品未上架");
    const order: BillingOrder = { id: `order-${++this.counter}`, userId, product: structuredClone(product), channel, status: "awaiting_payment", createdAtMs: nowMs, expiresAtMs: nowMs + 30 * 60_000 };
    this.orders.set(order.id, order); return order;
  }

  submitProof(userId: string, orderId: string, proofFingerprint: string, transactionReference: string) {
    const order = this.userOrder(userId, orderId); if (order.status !== "awaiting_payment" && order.status !== "rejected") throw new BillingError("invalid-state", "订单当前不能提交凭证");
    if (this.proofFingerprints.has(proofFingerprint)) throw new BillingError("duplicate-proof", "付款凭证已用于其他订单");
    this.proofFingerprints.add(proofFingerprint);
    const next: BillingOrder = { ...order, status: "under_review", proofFingerprint, transactionReference }; this.orders.set(orderId, next); return next;
  }

  reviewOrder(reviewerRole: "support" | "payment-reviewer", orderId: string, approved: boolean, nowMs = Date.now()) {
    if (reviewerRole !== "payment-reviewer") throw new BillingError("forbidden", "没有付款审核权限");
    const order = this.order(orderId); if (order.status === "paid") return order;
    if (order.status !== "under_review") throw new BillingError("invalid-state", "订单不在审核中");
    if (!approved) { const rejected: BillingOrder = { ...order, status: "rejected" }; this.orders.set(orderId, rejected); return rejected; }
    const paid: BillingOrder = { ...order, status: "paid" }; this.orders.set(orderId, paid); this.activateOrder(paid, nowMs); return paid;
  }

  userOrders(userId: string) { return [...this.orders.values()].filter(order => order.userId === userId); }
  activateVerifiedProduct(userId: string, product: BillingProduct, verifiedOrderId: string, nowMs = Date.now()) {
    const order: BillingOrder = { id: verifiedOrderId, userId, product: structuredClone(product), channel: "wechat", status: "paid", createdAtMs: nowMs, expiresAtMs: nowMs };
    this.activateOrder(order, nowMs); return order;
  }
  private activateOrder(order: BillingOrder, nowMs: number) {
    if (this.activatedOrders.has(order.id)) return; this.activatedOrders.add(order.id);
    if (order.product.kind === "points_pack") this.addEntry(order.userId, "purchase_credit", order.product.points!, order.id, `${order.product.displayName}到账`, nowMs);
    else {
      const currentEnd = Math.max(nowMs, ...(this.passes.get(order.userId) ?? []).map(pass => pass.endsAtMs));
      const pass: TimePassEntitlement = { id: `entitlement:${order.id}`, userId: order.userId, productId: order.product.id, startsAtMs: currentEnd, endsAtMs: currentEnd + order.product.durationDays! * DAY_MS, orderId: order.id, knowledgeAllowanceGranted: order.product.knowledgeIndexAllowance ?? 0, knowledgeAllowanceUsed: 0, knowledgeAllowanceLocked: 0 };
      this.passes.set(order.userId, [...(this.passes.get(order.userId) ?? []), pass]);
    }
  }

  private addEntry(userId: string, kind: LedgerEntryKind, points: number, referenceId: string, description: string, createdAtMs: number) {
    const existing = this.entries(userId).find(entry => entry.kind === kind && entry.referenceId === referenceId); if (existing) return existing;
    const entry: PointsLedgerEntry = { id: `ledger-${++this.counter}`, userId, kind, points, createdAtMs, referenceId, description };
    this.ledger.set(userId, [...this.entries(userId), entry]); return entry;
  }
  private product(id: string) { const value = this.products.get(id); if (!value) throw new BillingError("not-found", "商品不存在"); return value; }
  private order(id: string) { const value = this.orders.get(id); if (!value) throw new BillingError("not-found", "订单不存在"); return value; }
  private userOrder(userId: string, orderId: string) { const value = this.order(orderId); if (value.userId !== userId) throw new BillingError("forbidden", "无权访问订单"); return value; }
  private usage(id: string) { const value = this.usages.get(id); if (!value) throw new BillingError("not-found", "用量不存在"); return value; }
  private updatePass(id: string, update: (value: TimePassEntitlement) => TimePassEntitlement) { for (const [userId, passes] of this.passes) { const index = passes.findIndex(pass => pass.id === id); if (index >= 0) { const next = [...passes]; next[index] = update(next[index]!); this.passes.set(userId, next); return next[index]!; } } throw new BillingError("not-found", "会员权益不存在"); }
  private validateProduct(product: BillingProduct) {
    if (!Number.isInteger(product.priceCents) || product.priceCents <= 0) throw new BillingError("invalid-state", "价格必须是正整数分");
    if (product.kind === "points_pack" && (!product.points || !Number.isInteger(product.points))) throw new BillingError("invalid-state", "积分包配置无效");
    if (product.kind === "time_pass" && ![3, 7, 15, 30].includes(product.durationDays ?? 0)) throw new BillingError("invalid-state", "会员天数无效");
  }
}
