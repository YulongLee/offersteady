import { describe, expect, it } from "vitest";
import { BillingError, BillingService } from "../src/billing-service.js";
import {
  BillingRedemptionWallet,
  HmacCodeDigestAdapter,
  InMemoryOneTimeExportStore,
  InMemoryRedemptionRateLimiter,
  RedemptionAuthorizationError,
  RedemptionService,
  RedemptionValidationError,
  formatRedemptionCode,
  normalizeRedemptionCode,
  type CryptographicRandomSource,
  type RedemptionWallet,
} from "../src/redemption-service.js";

const NOW = 1_800_000_000_000;
const operator = { operatorId: "synthetic-operator", role: "redemption-operator" as const, recentlyVerified: true };
const context = (userId = "synthetic-user", at = NOW) => ({ userId, csrfValid: true, riskSourceHash: `risk-${userId}`, requestedAtMs: at });

class SequenceRandom implements CryptographicRandomSource {
  calls = 0;
  bytes(length: number) { const value = new Uint8Array(length); value.fill(++this.calls); return value; }
}

const setup = (options: { wallet?: RedemptionWallet; limiter?: InMemoryRedemptionRateLimiter; random?: CryptographicRandomSource; points?: number; count?: number; budget?: number; startsAtMs?: number; expiresAtMs?: number } = {}) => {
  const billing = new BillingService(); const random = options.random ?? new SequenceRandom();
  const service = new RedemptionService(options.wallet ?? new BillingRedemptionWallet(billing), new HmacCodeDigestAdapter(7, ["synthetic", "only", "test", "key"].join("-")), random, new InMemoryOneTimeExportStore(), options.limiter);
  const campaign = service.createCampaign(operator, { pointsPerCode: options.points ?? 120, codeLimit: options.count ?? 3, pointsBudget: options.budget ?? 360, startsAtMs: options.startsAtMs ?? NOW - 1_000, expiresAtMs: options.expiresAtMs ?? NOW + 60_000 }, NOW - 2_000);
  const batch = service.generateCodes(operator, campaign.id, options.count ?? 3, NOW - 1_500);
  const codes = service.readExport(operator, batch.oneTimeExport.id, NOW - 1_000)!;
  return { service, billing, campaign, batch, codes, random };
};

describe("redemption code generation and administration", () => {
  it("uses at least 80 random bits and normalizes only permitted separators", () => {
    const formatted = formatRedemptionCode(new Uint8Array(10).fill(9));
    expect(formatted).toMatch(/^[0-9A-HJKMNP-TV-Z]{4}(?:-[0-9A-HJKMNP-TV-Z]{4}){3}$/);
    expect(normalizeRedemptionCode(` ${formatted.toLowerCase()} `)).toBe(formatted.replaceAll("-", ""));
    expect(normalizeRedemptionCode(formatted.replace("-", "_"))).toBeNull();
    expect(() => formatRedemptionCode(new Uint8Array(9))).toThrow(/80 bits/);
  });

  it("persists unique keyed digests and safe hints, never plaintext fields", () => {
    const { service, random, codes } = setup();
    expect((random as SequenceRandom).calls).toBe(3); expect(new Set(codes).size).toBe(3);
    for (const record of service.codeRecords()) {
      expect(record.digest).toMatch(/^[a-f0-9]{64}$/); expect(record.publicHint).toMatch(/^••••-/);
      expect(record).not.toHaveProperty("code"); expect(record).not.toHaveProperty("plaintext");
    }
  });

  it("bounds collision retries without partially persisting a failed batch", () => {
    const duplicateRandom = { bytes: (length: number) => new Uint8Array(length) };
    const billing = new BillingService(); const service = new RedemptionService(new BillingRedemptionWallet(billing), new HmacCodeDigestAdapter(1, ["synthetic", "collision", "key"].join("-")), duplicateRandom, new InMemoryOneTimeExportStore(), new InMemoryRedemptionRateLimiter(), { maxPointsPerCode: 10_000, maxCodeCount: 100, maxPointsBudget: 1_000_000, maxCollisionRetries: 2 });
    const campaign = service.createCampaign(operator, { pointsPerCode: 10, codeLimit: 2, pointsBudget: 20, startsAtMs: NOW, expiresAtMs: NOW + 10_000 }, NOW);
    expect(() => service.generateCodes(operator, campaign.id, 2, NOW)).toThrow(RedemptionValidationError);
    expect(service.codeRecords()).toHaveLength(0);
  });

  it("validates policy, lifecycle and single-read export authorization", () => {
    const billing = new BillingService(); const service = new RedemptionService(new BillingRedemptionWallet(billing), new HmacCodeDigestAdapter(1, ["synthetic", "admin", "key"].join("-")), new SequenceRandom());
    expect(() => service.createCampaign(operator, { pointsPerCode: 0, codeLimit: 1, pointsBudget: 1, startsAtMs: NOW, expiresAtMs: NOW + 1 }, NOW)).toThrow(RedemptionValidationError);
    expect(() => service.createCampaign(operator, { pointsPerCode: 10, codeLimit: 2, pointsBudget: 10, startsAtMs: NOW, expiresAtMs: NOW + 1 }, NOW)).toThrow(RedemptionValidationError);
    expect(() => service.createCampaign({ operatorId: "synthetic-support", role: "support", recentlyVerified: true }, { pointsPerCode: 10, codeLimit: 1, pointsBudget: 10, startsAtMs: NOW, expiresAtMs: NOW + 1 }, NOW)).toThrow(RedemptionAuthorizationError);
    const campaign = service.createCampaign(operator, { pointsPerCode: 10, codeLimit: 1, pointsBudget: 10, startsAtMs: NOW, expiresAtMs: NOW + 10_000 }, NOW);
    const batch = service.generateCodes(operator, campaign.id, 1, NOW);
    expect(service.readExport(operator, batch.oneTimeExport.id, NOW)).toHaveLength(1); expect(service.readExport(operator, batch.oneTimeExport.id, NOW)).toBeNull();
    expect(service.activateCampaign(operator, campaign.id, NOW).status).toBe("active"); expect(service.pauseCampaign(operator, campaign.id, NOW).status).toBe("paused"); expect(service.resumeCampaign(operator, campaign.id, NOW).status).toBe("active"); expect(service.revokeCampaign(operator, campaign.id, NOW).status).toBe("revoked");
    expect(() => service.resumeCampaign(operator, campaign.id, NOW)).toThrow(RedemptionValidationError);
    expect(service.audits().every(event => !JSON.stringify(event).includes("synthetic-admin-key"))).toBe(true);
  });

  it("destroys an expired export without revealing its contents", () => {
    const store = new InMemoryOneTimeExportStore(); const item = store.put(["SYNTHETIC-NON-PRODUCTION"], NOW, 10);
    expect(store.take(item.id, NOW + 11)).toBeNull(); expect(store.take(item.id, NOW + 12)).toBeNull();
  });
});

describe("atomic points redemption", () => {
  it("credits exactly once and returns original data for owner replays", () => {
    const { service, billing, campaign, codes } = setup(); service.activateCampaign(operator, campaign.id, NOW - 500);
    const first = service.redeem({ code: codes[0]!, idempotencyKey: "synthetic-request-1" }, context());
    const replay = service.redeem({ code: "does-not-matter", idempotencyKey: "synthetic-request-1" }, context());
    const resubmit = service.redeem({ code: codes[0]!, idempotencyKey: "synthetic-request-2" }, context());
    expect(first.outcome).toBe("redeemed"); expect(replay).toEqual(first); expect(resubmit.outcome).toBe("already-redeemed-by-you");
    expect(billing.balance("synthetic-user")).toBe(120); expect(billing.entries("synthetic-user").filter(entry => entry.kind === "redemption_credit")).toHaveLength(1);
  });

  it("allows one winner for same-code races and hides ownership from another account", async () => {
    const { service, billing, campaign, codes } = setup(); service.activateCampaign(operator, campaign.id, NOW - 500);
    const [left, right] = await Promise.all([
      Promise.resolve().then(() => service.redeem({ code: codes[0]!, idempotencyKey: "race-a" }, context("synthetic-a"))),
      Promise.resolve().then(() => service.redeem({ code: codes[0]!, idempotencyKey: "race-b" }, context("synthetic-b"))),
    ]);
    expect([left.outcome, right.outcome].sort()).toEqual(["code-unavailable", "redeemed"]);
    expect([...billing.entries("synthetic-a"), ...billing.entries("synthetic-b")].filter(entry => entry.kind === "redemption_credit")).toHaveLength(1);
    const loser = left.outcome === "code-unavailable" ? left : right; expect(loser).toEqual({ outcome: "code-unavailable" });
  });

  it("rolls back all redemption state when wallet credit fails", () => {
    let fail = true; const billing = new BillingService(); const base = new BillingRedemptionWallet(billing);
    const wallet: RedemptionWallet = { balance: id => base.balance(id), entries: id => base.entries(id), credit: (...args) => { if (fail) throw new Error("synthetic wallet outage"); return base.credit(...args); }, reverse: (...args) => base.reverse(...args) };
    const { service, campaign, codes } = setup({ wallet }); service.activateCampaign(operator, campaign.id, NOW - 500);
    expect(service.redeem({ code: codes[0]!, idempotencyKey: "failure" }, context())).toEqual({ outcome: "temporarily-unavailable" });
    expect(service.codeRecords()[0]?.status).toBe("active"); expect(service.safeCampaign(campaign.id).redeemedCount).toBe(0); expect(billing.balance("synthetic-user")).toBe(0);
    fail = false; expect(service.redeem({ code: codes[0]!, idempotencyKey: "retry" }, context()).outcome).toBe("redeemed");
  });

  it.each([
    ["future", { startsAtMs: NOW + 100, expiresAtMs: NOW + 1_000 }],
    ["expired", { startsAtMs: NOW - 1_000, expiresAtMs: NOW }],
  ])("returns one generic result for %s campaign", (_name, dates) => {
    const { service, campaign, codes } = setup(dates); service.activateCampaign(operator, campaign.id, NOW - 500);
    expect(service.redeem({ code: codes[0]!, idempotencyKey: `date-${_name}` }, context())).toEqual({ outcome: "code-unavailable" });
  });

  it("returns the same generic result for paused, revoked and exhausted states", () => {
    const paused = setup(); paused.service.activateCampaign(operator, paused.campaign.id, NOW - 500); paused.service.pauseCampaign(operator, paused.campaign.id, NOW - 400);
    expect(paused.service.redeem({ code: paused.codes[0]!, idempotencyKey: "paused" }, context())).toEqual({ outcome: "code-unavailable" });
    paused.service.resumeCampaign(operator, paused.campaign.id, NOW); paused.service.revokeCampaign(operator, paused.campaign.id, NOW);
    expect(paused.service.redeem({ code: paused.codes[1]!, idempotencyKey: "revoked" }, context())).toEqual({ outcome: "code-unavailable" });
    const exhausted = setup({ count: 1, budget: 120 }); exhausted.service.activateCampaign(operator, exhausted.campaign.id, NOW - 500); exhausted.service.redeem({ code: exhausted.codes[0]!, idempotencyKey: "winner" }, context("synthetic-first"));
    expect(exhausted.service.safeCampaign(exhausted.campaign.id).redeemedPoints).toBe(120);
  });

  it("preserves membership precedence and supports linked non-negative reversal", () => {
    const { service, billing, campaign, codes } = setup(); const product = billing.catalog().find(item => item.kind === "time_pass")!; billing.activateVerifiedProduct("synthetic-member", product, "synthetic-paid-order", NOW - 1_000); service.activateCampaign(operator, campaign.id, NOW - 500);
    const result = service.redeem({ code: codes[0]!, idempotencyKey: "member" }, context("synthetic-member")); expect(result.outcome).toBe("redeemed");
    const usage = billing.reserveUsage("synthetic-member", "synthetic-answer", "answer", NOW); expect(usage.source).toBe("time_pass"); expect(billing.balance("synthetic-member")).toBe(120);
    const id = result.outcome === "redeemed" ? result.data.redemptionId : ""; const reversal = service.reverseRedemption(operator, id, "synthetic-fraud-review", NOW + 1); expect(reversal.kind).toBe("redemption_reversal"); expect(billing.balance("synthetic-member")).toBe(0); expect(billing.entries("synthetic-member").map(entry => entry.kind)).toContain("redemption_credit");
    expect(() => service.reverseRedemption(operator, id, "duplicate", NOW + 2)).toThrow(BillingError);
  });
});

describe("redemption abuse and privacy controls", () => {
  it("rejects authentication and CSRF failures without lookup details", () => {
    const { service } = setup();
    expect(service.redeem({ code: "SYNTHETIC-NOT-A-CODE", idempotencyKey: "auth" }, { ...context(), userId: null })).toEqual({ outcome: "code-unavailable" });
    expect(service.redeem({ code: "SYNTHETIC-NOT-A-CODE", idempotencyKey: "csrf" }, { ...context(), csrfValid: false })).toEqual({ outcome: "code-unavailable" });
  });

  it("limits repeated failures by account and shared risk source before lookup", () => {
    const limiter = new InMemoryRedemptionRateLimiter(2, 60_000); const { service } = setup({ limiter });
    const invalid = "0".repeat(16);
    expect(service.redeem({ code: invalid, idempotencyKey: "bad-1" }, context()).outcome).toBe("code-unavailable");
    expect(service.redeem({ code: invalid, idempotencyKey: "bad-2" }, context()).outcome).toBe("code-unavailable");
    const blocked = service.redeem({ code: invalid, idempotencyKey: "bad-3" }, context("synthetic-user", NOW + 1)); expect(blocked.outcome).toBe("rate-limited");
    const shared = { ...context("synthetic-other", NOW + 1), riskSourceHash: "risk-synthetic-user" }; expect(service.redeem({ code: invalid, idempotencyKey: "shared" }, shared).outcome).toBe("rate-limited");
  });

  it("records only safe metrics, audit and cross-account prefix signals", () => {
    const { service } = setup(); const input = "1".repeat(16);
    for (const user of ["synthetic-a", "synthetic-b", "synthetic-c"]) service.redeem({ code: input, idempotencyKey: user }, context(user));
    expect(service.riskSignals()[0]).toMatchObject({ category: "cross-account-similar-prefix", accountCount: 3 });
    const exported = JSON.stringify({ metrics: service.metrics(), audits: service.audits(), signals: service.riskSignals() });
    expect(exported).not.toContain(input); expect(exported).not.toContain("synthetic-only-test-key"); expect(exported).not.toContain("synthetic-a");
  });

  it("keeps support read-only and excludes digest and plaintext", () => {
    const { service, batch } = setup(); const found = service.supportLookup({ operatorId: "synthetic-support", role: "support", recentlyVerified: false }, batch.publicHints[0]!);
    expect(found).toHaveLength(1); expect(found[0]).not.toHaveProperty("digest"); expect(found[0]).not.toHaveProperty("code");
    expect(() => service.supportLookup({ operatorId: "synthetic-user", role: "user", recentlyVerified: true }, batch.publicHints[0]!)).toThrow(RedemptionAuthorizationError);
  });
});
