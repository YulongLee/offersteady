import type { PointsLedgerEntry } from "./billing.js";

export type RedemptionCampaignStatus = "draft" | "active" | "paused" | "revoked";
export type RedemptionCodeStatus = "active" | "redeemed" | "revoked";
export type RedemptionOperatorRole = "redemption-operator" | "support" | "user";

export interface PointsRedemptionRequest {
  readonly code: string;
  readonly idempotencyKey: string;
}

export interface RedemptionRequestContext {
  readonly userId: string | null;
  readonly csrfValid: boolean;
  readonly riskSourceHash: string;
  readonly requestedAtMs: number;
}

export interface RedemptionSuccessData {
  readonly redemptionId: string;
  readonly points: number;
  readonly newBalance: number;
  readonly publicHint: string;
  readonly redeemedAtMs: number;
  readonly ledgerEntry: PointsLedgerEntry;
}

export type PointsRedemptionResult =
  | { readonly outcome: "redeemed"; readonly data: RedemptionSuccessData }
  | { readonly outcome: "already-redeemed-by-you"; readonly data: RedemptionSuccessData }
  | { readonly outcome: "code-unavailable" }
  | { readonly outcome: "rate-limited"; readonly retryAfterMs: number }
  | { readonly outcome: "temporarily-unavailable" };

export interface RedemptionCampaign {
  readonly id: string;
  readonly status: RedemptionCampaignStatus;
  readonly pointsPerCode: number;
  readonly codeLimit: number;
  readonly pointsBudget: number;
  readonly startsAtMs: number;
  readonly expiresAtMs: number;
  readonly redeemedCount: number;
  readonly redeemedPoints: number;
  readonly createdAtMs: number;
}

export interface RedemptionCodeRecord {
  readonly id: string;
  readonly campaignId: string;
  readonly digest: string;
  readonly pepperVersion: number;
  readonly publicHint: string;
  readonly status: RedemptionCodeStatus;
  readonly createdAtMs: number;
  readonly redeemedByUserId?: string;
  readonly redeemedAtMs?: number;
}

export interface RedemptionRecord {
  readonly id: string;
  readonly codeId: string;
  readonly campaignId: string;
  readonly userId: string;
  readonly points: number;
  readonly publicHint: string;
  readonly redeemedAtMs: number;
  readonly ledgerReferenceId: string;
}

export interface RedemptionOperatorContext {
  readonly operatorId: string;
  readonly role: RedemptionOperatorRole;
  readonly recentlyVerified: boolean;
}

export type RedemptionAdministrationCommand =
  | { readonly type: "create-campaign"; readonly idempotencyKey: string; readonly pointsPerCode: number; readonly codeLimit: number; readonly pointsBudget: number; readonly startsAtMs: number; readonly expiresAtMs: number }
  | { readonly type: "activate-campaign" | "pause-campaign" | "resume-campaign" | "revoke-campaign"; readonly idempotencyKey: string; readonly campaignId: string; readonly reason: string }
  | { readonly type: "generate-codes"; readonly idempotencyKey: string; readonly campaignId: string; readonly count: number }
  | { readonly type: "read-export"; readonly idempotencyKey: string; readonly exportId: string }
  | { readonly type: "reverse-redemption"; readonly idempotencyKey: string; readonly redemptionId: string; readonly reason: string };

export interface RedemptionAuditEvent {
  readonly id: string;
  readonly action: RedemptionAdministrationCommand["type"] | "redeem";
  readonly actorHash: string;
  readonly targetId: string;
  readonly result: "succeeded" | "rejected";
  readonly reason: string;
  readonly createdAtMs: number;
}
