export type GlobalOfferCode =
  | "global-free"
  | "global-interview-pass"
  | "global-pro-weekly"
  | "global-pro-monthly"
  | "global-job-hunt";

export type GlobalBillingMode = "free" | "one_time" | "recurring";
export type GlobalCommerceMode = "test" | "live";
export type GlobalCommerceProvider = "creem";

export interface GlobalPlanBenefits {
  readonly copilotMinutes: number | null;
  readonly screenAssistUses: number | null;
  readonly resumeAndJobDescription: boolean;
  readonly knowledgeBase: boolean;
  readonly knowledgeTokens?: number;
  readonly writtenExam: boolean;
  readonly fullProduct: boolean;
}

export interface GlobalPlanVersion {
  readonly offerCode: GlobalOfferCode;
  readonly version: number;
  readonly displayName: string;
  readonly description: string;
  readonly currency: "USD";
  readonly priceCents: number;
  readonly billingMode: GlobalBillingMode;
  readonly durationDays: number | null;
  readonly benefits: GlobalPlanBenefits;
  readonly published: boolean;
  readonly featured: boolean;
  readonly displayOrder: number;
  readonly createdAtMs: number;
}

export type GlobalEntitlementStatus = "active" | "exhausted" | "expired" | "revoked";

export interface GlobalEntitlement {
  readonly id: string;
  readonly offerCode: GlobalOfferCode;
  readonly planVersion: number;
  readonly status: GlobalEntitlementStatus;
  readonly startsAtMs: number;
  readonly endsAtMs: number | null;
  readonly copilotMinutesRemaining: number | null;
  readonly screenAssistUsesRemaining: number | null;
  readonly knowledgeTokensRemaining?: number;
  readonly benefits: GlobalPlanBenefits;
  readonly subscriptionId?: string;
  readonly cancelsAtMs?: number;
}

export type GlobalCommerceOrderStatus =
  | "pending"
  | "checkout_created"
  | "confirming"
  | "paid"
  | "failed"
  | "expired"
  | "refunded"
  | "disputed";

export interface GlobalCommerceOrder {
  readonly id: string;
  readonly offerCode: GlobalOfferCode;
  readonly planVersion: number;
  readonly status: GlobalCommerceOrderStatus;
  readonly amountCents: number;
  readonly currency: "USD";
  readonly mode: GlobalCommerceMode;
  readonly createdAtMs: number;
  readonly updatedAtMs: number;
  readonly checkoutUrl?: string;
  readonly providerOrderId?: string;
  readonly providerSubscriptionId?: string;
}

export interface GlobalSubscription {
  readonly id: string;
  readonly offerCode: GlobalOfferCode;
  readonly status: "trialing" | "active" | "past_due" | "unpaid" | "canceling" | "canceled" | "paused" | "expired";
  readonly currentPeriodStartMs: number;
  readonly currentPeriodEndMs: number;
  readonly canceledAtMs?: number;
}

export interface GlobalUsageSummary {
  readonly copilotMinutesRemaining: number | null;
  readonly screenAssistUsesRemaining: number | null;
  readonly copilotUnlimited: boolean;
  readonly screenAssistUnlimited: boolean;
  readonly knowledgeTokensRemaining: number;
  readonly knowledgeTokensUnlimited: boolean;
}

export interface GlobalCommerceState {
  readonly enabled: boolean;
  readonly provider: GlobalCommerceProvider | "none";
  readonly mode: GlobalCommerceMode;
  readonly plans: readonly GlobalPlanVersion[];
  readonly entitlement: GlobalEntitlement | null;
  readonly usage: GlobalUsageSummary | null;
  readonly subscription: GlobalSubscription | null;
  readonly orders: readonly GlobalCommerceOrder[];
  readonly fairUsePolicyUrl: string;
  readonly refundPolicyUrl: string;
  readonly termsUrl: string;
  readonly privacyUrl: string;
  readonly supportEmail: string;
}

export interface GlobalCommerceReadiness {
  readonly edition: "global";
  readonly mode: GlobalCommerceMode;
  readonly enabled: boolean;
  readonly ready: boolean;
  readonly apiKeyConfigured: boolean;
  readonly webhookSecretConfigured: boolean;
  readonly webhookUrlConfigured: boolean;
  readonly legalLinksConfigured: boolean;
  readonly mappingsReady: boolean;
  readonly webhookAccepted: boolean;
  readonly secretFingerprint?: string;
  readonly blockers: readonly string[];
}
