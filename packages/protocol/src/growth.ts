import type { BillingProduct, PaymentChannel } from "./billing.js";

export type AuthorizationSessionStatus = "creating" | "waiting" | "scanned" | "authorized" | "expired" | "closed" | "failed";
export interface WechatAuthorizationSession {
  readonly id: string;
  readonly state: string;
  readonly status: AuthorizationSessionStatus;
  readonly authorizeUrl: string;
  readonly expiresAtMs: number;
}
export interface AuthorizationPopupResult {
  readonly sessionId: string;
  readonly status: "authorized" | "failed" | "closed";
  readonly accountId?: string;
  readonly safeErrorCode?: string;
}

export type OfficialCheckoutStatus = "created" | "payment_pending" | "paid" | "failed" | "closed" | "refund_pending" | "refunded";
export type OfficialCheckoutAction =
  | { readonly kind: "dynamic_qr"; readonly value: string; readonly expiresAtMs: number }
  | { readonly kind: "redirect"; readonly url: string; readonly expiresAtMs: number };
export interface OfficialCheckoutOrder {
  readonly id: string;
  readonly userId: string;
  readonly product: BillingProduct;
  readonly amountCents: number;
  readonly currency: "CNY";
  readonly channel: PaymentChannel;
  readonly status: OfficialCheckoutStatus;
  readonly action: OfficialCheckoutAction;
  readonly createdAtMs: number;
  readonly updatedAtMs: number;
}
export interface VerifiedPaymentNotification {
  readonly providerEventId: string;
  readonly orderId: string;
  readonly merchantId: string;
  readonly applicationId: string;
  readonly amountCents: number;
  readonly currency: "CNY";
  readonly paid: boolean;
  readonly verified: boolean;
}

export type ReadinessCheck = "signed-artifact" | "install-lifecycle" | "protocol" | "identity" | "pairing" | "reconnect" | "microphone" | "system-audio" | "physical-devices";
export interface WindowsSupportEvidence { readonly check: ReadinessCheck; readonly passed: boolean; readonly releaseVersion: string; readonly verifiedAtMs: number; readonly expiresAtMs: number }
export interface WindowsSupportReadiness { readonly releaseVersion: string; readonly status: "supported" | "limited" | "not-ready" | "revoked"; readonly evidence: readonly WindowsSupportEvidence[]; readonly limitedReason?: string }

export type ProductAssetCategory = "brand" | "payments" | "support";
export interface ProductAssetEntry { readonly id: string; readonly category: ProductAssetCategory; readonly path: string; readonly purpose: string; readonly alt: string; readonly width: number; readonly height: number; readonly sha256: string; readonly version: number; readonly public: boolean; readonly expiresAtMs?: number }
export interface ProductAssetManifest { readonly version: number; readonly entries: readonly ProductAssetEntry[] }

export interface GuideChapter { readonly id: string; readonly title: string; readonly keywords: readonly string[]; readonly summary: string; readonly sections: readonly { readonly id: string; readonly title: string; readonly paragraphs: readonly string[] }[] }
export interface GuideContent { readonly version: string; readonly locale: "zh-CN"; readonly chapters: readonly GuideChapter[] }
