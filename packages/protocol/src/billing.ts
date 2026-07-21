export type BillingProductKind = "points_pack" | "time_pass";
export type PaymentChannel = "wechat" | "alipay";
export type BillingOrderStatus = "awaiting_payment" | "proof_submitted" | "under_review" | "paid" | "rejected" | "expired" | "refund_pending" | "refunded";
export type LedgerEntryKind = "welcome_grant" | "purchase_credit" | "redemption_credit" | "redemption_reversal" | "usage_reserve" | "usage_settle" | "usage_release" | "refund_debit" | "support_adjustment";
export type BillableOperationKind = "answer" | "screenshot_answer" | "knowledge_index";

export interface BillingProduct {
  readonly id: string;
  readonly catalogVersion: number;
  readonly kind: BillingProductKind;
  readonly displayName: string;
  readonly priceCents: number;
  readonly points?: number;
  readonly durationDays?: 3 | 7 | 15 | 30;
  readonly knowledgeIndexAllowance?: 0 | 2;
  readonly published: boolean;
}

export interface UsageRates {
  readonly catalogVersion: number;
  readonly answerPoints: number;
  readonly screenshotAnswerPoints: number;
  readonly knowledgeIndexMinimumPoints: number;
  readonly knowledgeIndexPointsPer1000Tokens: number;
  readonly tokenizerVersion: string;
}

export interface PointsLedgerEntry {
  readonly id: string;
  readonly userId: string;
  readonly kind: LedgerEntryKind;
  readonly points: number;
  readonly createdAtMs: number;
  readonly referenceId: string;
  readonly description: string;
}

export interface TimePassEntitlement {
  readonly id: string;
  readonly userId: string;
  readonly productId: string;
  readonly startsAtMs: number;
  readonly endsAtMs: number;
  readonly orderId: string;
  readonly knowledgeAllowanceGranted: number;
  readonly knowledgeAllowanceUsed: number;
  readonly knowledgeAllowanceLocked: number;
}

export interface UsageCharge {
  readonly usageId: string;
  readonly userId: string;
  readonly kind: BillableOperationKind;
  readonly points: number;
  readonly source: "points" | "time_pass" | "pass_allowance";
  readonly status: "reserved" | "settled" | "released";
  readonly catalogVersion: number;
  readonly documentVersionId?: string;
  readonly entitlementId?: string;
  readonly quoteId?: string;
  readonly tokenCount?: number;
  readonly tokenizerVersion?: string;
}

export interface BillingOrder {
  readonly id: string;
  readonly userId: string;
  readonly product: BillingProduct;
  readonly channel: PaymentChannel;
  readonly status: BillingOrderStatus;
  readonly createdAtMs: number;
  readonly expiresAtMs: number;
  readonly proofFingerprint?: string;
  readonly transactionReference?: string;
}

export interface BillingSupportConfig {
  readonly wechatId: string;
  readonly email: string;
  readonly qrAssetPath: string;
  readonly serviceHours: string;
  readonly refundSummary: string;
}
