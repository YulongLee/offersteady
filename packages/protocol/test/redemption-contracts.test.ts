import { describe, expect, it } from "vitest";
import type { PointsRedemptionRequest, RedemptionCodeRecord, RedemptionCampaign, PointsRedemptionResult } from "../src/index.js";

describe("points redemption contracts", () => {
  it("keeps client request limited to code and idempotency metadata", () => {
    const request: PointsRedemptionRequest = { code: "SYNTH-ETIC-CODE-ONLY", idempotencyKey: "synthetic-request-1" };
    expect(Object.keys(request).sort()).toEqual(["code", "idempotencyKey"]);
    expect(request).not.toHaveProperty("points");
  });

  it("stores a keyed digest and public hint without a plaintext field", () => {
    const record: RedemptionCodeRecord = { id: "code-1", campaignId: "campaign-1", digest: "synthetic-digest", pepperVersion: 1, publicHint: "••••-TEST", status: "active", createdAtMs: 1 };
    expect(record).not.toHaveProperty("code");
    expect(record).not.toHaveProperty("plaintext");
  });

  it("serializes campaign limits and safe public outcomes", () => {
    const campaign: RedemptionCampaign = { id: "campaign-1", status: "active", pointsPerCode: 100, codeLimit: 10, pointsBudget: 1000, startsAtMs: 1, expiresAtMs: 100, redeemedCount: 0, redeemedPoints: 0, createdAtMs: 1 };
    const unavailable: PointsRedemptionResult = { outcome: "code-unavailable" };
    expect(JSON.parse(JSON.stringify(campaign))).toEqual(campaign);
    expect(unavailable).toEqual({ outcome: "code-unavailable" });
  });
});
