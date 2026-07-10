import { createCipheriv, createDecipheriv, createHmac, randomBytes } from "node:crypto";
import type {
  PointsLedgerEntry,
  PointsRedemptionRequest,
  PointsRedemptionResult,
  RedemptionAuditEvent,
  RedemptionCampaign,
  RedemptionCodeRecord,
  RedemptionOperatorContext,
  RedemptionRecord,
  RedemptionRequestContext,
} from "@offersteady/protocol";
import { BillingError, BillingService } from "./billing-service.js";

const ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ";
const NORMALIZED_LENGTH = 16;

export interface CryptographicRandomSource { bytes(length: number): Uint8Array }
export class NodeCryptographicRandomSource implements CryptographicRandomSource {
  bytes(length: number) { return randomBytes(length); }
}

export interface KeyedDigestAdapter { readonly version: number; digest(normalizedCode: string): string }
export class HmacCodeDigestAdapter implements KeyedDigestAdapter {
  constructor(readonly version: number, private readonly serverPepper: string) {
    if (!serverPepper) throw new Error("Server-managed redemption pepper is required");
  }
  digest(normalizedCode: string) { return createHmac("sha256", this.serverPepper).update(normalizedCode).digest("hex"); }
}

export const normalizeRedemptionCode = (input: string) => {
  const normalized = input.toUpperCase().replace(/[ -]/g, "");
  return normalized.length === NORMALIZED_LENGTH && [...normalized].every(character => ALPHABET.includes(character)) ? normalized : null;
};

export const formatRedemptionCode = (bytes: Uint8Array) => {
  if (bytes.byteLength < 10) throw new Error("At least 80 bits of entropy are required");
  let bits = 0; let buffer = 0; let value = "";
  for (const byte of bytes) {
    buffer = (buffer << 8) | byte; bits += 8;
    while (bits >= 5 && value.length < NORMALIZED_LENGTH) { bits -= 5; value += ALPHABET[(buffer >>> bits) & 31]; }
    buffer &= (1 << bits) - 1;
  }
  return value.match(/.{1,4}/g)!.join("-");
};

export interface RedemptionWallet {
  balance(userId: string): number;
  entries(userId: string): PointsLedgerEntry[];
  credit(userId: string, redemptionId: string, points: number, publicHint: string, nowMs: number): PointsLedgerEntry;
  reverse(userId: string, redemptionId: string, points: number, nowMs: number): PointsLedgerEntry;
}

export class BillingRedemptionWallet implements RedemptionWallet {
  constructor(private readonly billing: BillingService) {}
  balance(userId: string) { return this.billing.balance(userId); }
  entries(userId: string) { return this.billing.entries(userId); }
  credit(userId: string, redemptionId: string, points: number, publicHint: string, nowMs: number) { return this.billing.creditRedemption(userId, redemptionId, points, publicHint, nowMs); }
  reverse(userId: string, redemptionId: string, points: number, nowMs: number) { return this.billing.reverseRedemption(userId, redemptionId, points, nowMs); }
}

interface ExportEnvelope { readonly ciphertext: string; readonly expiresAtMs: number; read: boolean }
export class InMemoryOneTimeExportStore {
  private readonly values = new Map<string, ExportEnvelope>(); private readonly ephemeralKey = randomBytes(32); private counter = 0;
  put(codes: readonly string[], nowMs: number, ttlMs = 5 * 60_000) { const id = `export-${++this.counter}`; this.values.set(id, { ciphertext: this.seal(JSON.stringify(codes)), expiresAtMs: nowMs + ttlMs, read: false }); return { id, expiresAtMs: nowMs + ttlMs }; }
  take(id: string, nowMs: number) { const item = this.values.get(id); if (!item || item.read || item.expiresAtMs <= nowMs) { this.values.delete(id); return null; } item.read = true; this.values.delete(id); return JSON.parse(this.open(item.ciphertext)) as string[]; }
  private seal(plaintext: string) { const iv = randomBytes(12); const cipher = createCipheriv("aes-256-gcm", this.ephemeralKey, iv); const encrypted = Buffer.concat([cipher.update(plaintext, "utf8"), cipher.final()]); return Buffer.concat([iv, cipher.getAuthTag(), encrypted]).toString("base64"); }
  private open(value: string) { const payload = Buffer.from(value, "base64"); const decipher = createDecipheriv("aes-256-gcm", this.ephemeralKey, payload.subarray(0, 12)); decipher.setAuthTag(payload.subarray(12, 28)); return Buffer.concat([decipher.update(payload.subarray(28)), decipher.final()]).toString("utf8"); }
}

interface LimitBucket { failures: number; blockedUntilMs: number; windowStartedAtMs: number }
export class InMemoryRedemptionRateLimiter {
  private readonly account = new Map<string, LimitBucket>(); private readonly risk = new Map<string, LimitBucket>(); private readonly prefixSignals = new Map<string, Set<string>>();
  constructor(private readonly failureLimit = 5, private readonly windowMs = 60_000) {}
  check(userId: string, riskHash: string, nowMs: number) {
    const waits = [this.account.get(userId), this.risk.get(riskHash)].map(bucket => Math.max(0, (bucket?.blockedUntilMs ?? 0) - nowMs));
    return Math.max(...waits);
  }
  failure(userId: string, riskHash: string, prefixHash: string, nowMs: number) {
    this.bump(this.account, userId, nowMs); this.bump(this.risk, riskHash, nowMs);
    const accounts = this.prefixSignals.get(prefixHash) ?? new Set<string>(); accounts.add(this.safeHash(userId)); this.prefixSignals.set(prefixHash, accounts);
  }
  signals() { return [...this.prefixSignals].filter(([, accounts]) => accounts.size >= 3).map(([prefixHash, accounts]) => ({ category: "cross-account-similar-prefix" as const, prefixHash, accountCount: accounts.size })); }
  private bump(target: Map<string, LimitBucket>, key: string, nowMs: number) { let bucket = target.get(key); if (!bucket || nowMs - bucket.windowStartedAtMs >= this.windowMs) bucket = { failures: 0, blockedUntilMs: 0, windowStartedAtMs: nowMs }; bucket.failures += 1; if (bucket.failures >= this.failureLimit) bucket.blockedUntilMs = nowMs + Math.min(this.windowMs, 1_000 * 2 ** (bucket.failures - this.failureLimit)); target.set(key, bucket); }
  private safeHash(value: string) { return createHmac("sha256", "risk-domain").update(value).digest("hex").slice(0, 16); }
}

export class RedemptionAuthorizationError extends Error {}
export class RedemptionValidationError extends Error {}

export interface RedemptionPolicy { maxPointsPerCode: number; maxCodeCount: number; maxPointsBudget: number; maxCollisionRetries: number }
export interface CreateCampaignInput { pointsPerCode: number; codeLimit: number; pointsBudget: number; startsAtMs: number; expiresAtMs: number }
export interface RedemptionMetric { readonly outcome: PointsRedemptionResult["outcome"]; readonly latencyMs: number; readonly riskHash: string; readonly campaignBudget?: { redeemed: number; total: number } }

export class RedemptionService {
  private readonly campaigns = new Map<string, RedemptionCampaign>(); private readonly codesByDigest = new Map<string, RedemptionCodeRecord>(); private readonly codesById = new Map<string, RedemptionCodeRecord>(); private readonly redemptions = new Map<string, RedemptionRecord>(); private readonly redemptionByCode = new Map<string, string>(); private readonly replay = new Map<string, PointsRedemptionResult>(); private readonly auditTrail: RedemptionAuditEvent[] = []; private readonly observations: RedemptionMetric[] = []; private counter = 0;
  constructor(private readonly wallet: RedemptionWallet, private readonly digest: KeyedDigestAdapter, private readonly random: CryptographicRandomSource = new NodeCryptographicRandomSource(), private readonly exports = new InMemoryOneTimeExportStore(), private readonly limiter = new InMemoryRedemptionRateLimiter(), private readonly policy: RedemptionPolicy = { maxPointsPerCode: 10_000, maxCodeCount: 10_000, maxPointsBudget: 10_000_000, maxCollisionRetries: 8 }) {}

  createCampaign(operator: RedemptionOperatorContext, input: CreateCampaignInput, nowMs = Date.now()) {
    this.authorize(operator, "create-campaign", "new", nowMs); this.validateCampaign(input);
    const campaign: RedemptionCampaign = { id: `campaign-${++this.counter}`, status: "draft", ...input, redeemedCount: 0, redeemedPoints: 0, createdAtMs: nowMs };
    this.campaigns.set(campaign.id, campaign); this.audit(operator.operatorId, "create-campaign", campaign.id, "succeeded", "created", nowMs); return campaign;
  }
  activateCampaign(operator: RedemptionOperatorContext, campaignId: string, nowMs = Date.now()) { return this.transition(operator, campaignId, "activate-campaign", ["draft"], "active", nowMs); }
  pauseCampaign(operator: RedemptionOperatorContext, campaignId: string, nowMs = Date.now()) { return this.transition(operator, campaignId, "pause-campaign", ["active"], "paused", nowMs); }
  resumeCampaign(operator: RedemptionOperatorContext, campaignId: string, nowMs = Date.now()) { return this.transition(operator, campaignId, "resume-campaign", ["paused"], "active", nowMs); }
  revokeCampaign(operator: RedemptionOperatorContext, campaignId: string, nowMs = Date.now()) { return this.transition(operator, campaignId, "revoke-campaign", ["draft", "active", "paused"], "revoked", nowMs); }

  generateCodes(operator: RedemptionOperatorContext, campaignId: string, count: number, nowMs = Date.now()) {
    this.authorize(operator, "generate-codes", campaignId, nowMs); const campaign = this.requireCampaign(campaignId);
    if (campaign.status !== "draft" || !Number.isInteger(count) || count <= 0 || this.campaignCodeCount(campaignId) + count > campaign.codeLimit) throw new RedemptionValidationError("Generation exceeds campaign code limit or campaign is not draft");
    const plaintext: string[] = []; const records: RedemptionCodeRecord[] = [];
    for (let index = 0; index < count; index++) {
      let record: RedemptionCodeRecord | null = null;
      for (let attempt = 0; attempt < this.policy.maxCollisionRetries; attempt++) {
        const formatted = formatRedemptionCode(this.random.bytes(10)); const normalized = normalizeRedemptionCode(formatted)!; const digest = this.digest.digest(normalized);
        if (this.codesByDigest.has(digest) || records.some(item => item.digest === digest)) continue;
        record = { id: `code-${++this.counter}`, campaignId, digest, pepperVersion: this.digest.version, publicHint: `••••-${normalized.slice(-4)}`, status: "active", createdAtMs: nowMs }; plaintext.push(formatted); records.push(record); break;
      }
      if (!record) throw new RedemptionValidationError("Unable to generate a unique code batch");
    }
    for (const record of records) { this.codesByDigest.set(record.digest, record); this.codesById.set(record.id, record); }
    const oneTimeExport = this.exports.put(plaintext, nowMs); this.audit(operator.operatorId, "generate-codes", campaignId, "succeeded", `generated:${records.length}`, nowMs);
    return { generatedCount: records.length, publicHints: records.map(item => item.publicHint), oneTimeExport };
  }

  readExport(operator: RedemptionOperatorContext, exportId: string, nowMs = Date.now()) { this.authorize(operator, "read-export", exportId, nowMs); const codes = this.exports.take(exportId, nowMs); this.audit(operator.operatorId, "read-export", exportId, codes ? "succeeded" : "rejected", codes ? "single-read" : "unavailable", nowMs); return codes; }

  redeem(request: PointsRedemptionRequest, context: RedemptionRequestContext): PointsRedemptionResult {
    const started = Date.now();
    if (!context.userId || !context.csrfValid) return this.finish({ outcome: "code-unavailable" }, context, started);
    const replayKey = `${context.userId}:${request.idempotencyKey}`; const replay = this.replay.get(replayKey); if (replay) return replay;
    const wait = this.limiter.check(context.userId, context.riskSourceHash, context.requestedAtMs); if (wait > 0) return this.finish({ outcome: "rate-limited", retryAfterMs: wait }, context, started);
    const normalized = normalizeRedemptionCode(request.code); if (!normalized) { this.fail(context, "invalid-format"); return this.finish({ outcome: "code-unavailable" }, context, started); }
    const code = this.codesByDigest.get(this.digest.digest(normalized));
    if (!code) { this.fail(context, this.prefixHash(normalized)); return this.finish({ outcome: "code-unavailable" }, context, started); }
    const existingId = this.redemptionByCode.get(code.id); const existing = existingId ? this.redemptions.get(existingId) : undefined;
    if (existing) {
      if (existing.userId !== context.userId) { this.fail(context, this.prefixHash(normalized)); return this.finish({ outcome: "code-unavailable" }, context, started); }
      const result = this.success("already-redeemed-by-you", existing); this.replay.set(replayKey, result); return this.finish(result, context, started, existing.campaignId);
    }
    const campaign = this.requireCampaign(code.campaignId);
    if (code.status !== "active" || campaign.status !== "active" || context.requestedAtMs < campaign.startsAtMs || context.requestedAtMs >= campaign.expiresAtMs || campaign.redeemedCount >= campaign.codeLimit || campaign.redeemedPoints + campaign.pointsPerCode > campaign.pointsBudget) { this.fail(context, this.prefixHash(normalized)); return this.finish({ outcome: "code-unavailable" }, context, started, campaign.id); }
    const redemption: RedemptionRecord = { id: `redemption-${++this.counter}`, codeId: code.id, campaignId: campaign.id, userId: context.userId, points: campaign.pointsPerCode, publicHint: code.publicHint, redeemedAtMs: context.requestedAtMs, ledgerReferenceId: `redemption-${this.counter}` };
    try {
      const entry = this.wallet.credit(context.userId, redemption.id, redemption.points, redemption.publicHint, context.requestedAtMs);
      const nextCode: RedemptionCodeRecord = { ...code, status: "redeemed", redeemedByUserId: context.userId, redeemedAtMs: context.requestedAtMs };
      const nextCampaign: RedemptionCampaign = { ...campaign, redeemedCount: campaign.redeemedCount + 1, redeemedPoints: campaign.redeemedPoints + redemption.points };
      this.codesByDigest.set(code.digest, nextCode); this.codesById.set(code.id, nextCode); this.campaigns.set(campaign.id, nextCampaign); this.redemptions.set(redemption.id, redemption); this.redemptionByCode.set(code.id, redemption.id);
      const result: PointsRedemptionResult = { outcome: "redeemed", data: { redemptionId: redemption.id, points: redemption.points, newBalance: this.wallet.balance(context.userId), publicHint: redemption.publicHint, redeemedAtMs: redemption.redeemedAtMs, ledgerEntry: entry } };
      this.replay.set(replayKey, result); this.audit(this.safeActor(context.userId), "redeem", redemption.id, "succeeded", "credited", context.requestedAtMs); return this.finish(result, context, started, campaign.id);
    } catch { return this.finish({ outcome: "temporarily-unavailable" }, context, started, campaign.id); }
  }

  reverseRedemption(operator: RedemptionOperatorContext, redemptionId: string, reason: string, nowMs = Date.now()) { this.authorize(operator, "reverse-redemption", redemptionId, nowMs); const redemption = this.redemptions.get(redemptionId); if (!redemption) throw new RedemptionValidationError("Redemption not found"); const entry = this.wallet.reverse(redemption.userId, redemption.id, redemption.points, nowMs); this.audit(operator.operatorId, "reverse-redemption", redemptionId, "succeeded", reason, nowMs); return entry; }
  safeCampaign(campaignId: string) { const campaign = this.requireCampaign(campaignId); return { id: campaign.id, status: campaign.status, pointsPerCode: campaign.pointsPerCode, codeLimit: campaign.codeLimit, pointsBudget: campaign.pointsBudget, redeemedCount: campaign.redeemedCount, redeemedPoints: campaign.redeemedPoints, startsAtMs: campaign.startsAtMs, expiresAtMs: campaign.expiresAtMs }; }
  supportLookup(operator: RedemptionOperatorContext, publicHint: string) { if (operator.role !== "support" && operator.role !== "redemption-operator") throw new RedemptionAuthorizationError("Not authorized"); return [...this.codesById.values()].filter(code => code.publicHint === publicHint).map(code => ({ publicHint: code.publicHint, status: code.status, campaignId: code.campaignId, redeemed: code.status === "redeemed" })); }
  audits() { return structuredClone(this.auditTrail); }
  metrics() { return structuredClone(this.observations); }
  riskSignals() { return this.limiter.signals(); }
  codeRecords() { return structuredClone([...this.codesById.values()]); }

  private success(outcome: "already-redeemed-by-you", record: RedemptionRecord): PointsRedemptionResult { const entry = this.wallet.entries(record.userId).find(item => item.kind === "redemption_credit" && item.referenceId === record.id)!; return { outcome, data: { redemptionId: record.id, points: record.points, newBalance: this.wallet.balance(record.userId), publicHint: record.publicHint, redeemedAtMs: record.redeemedAtMs, ledgerEntry: entry } }; }
  private transition(operator: RedemptionOperatorContext, id: string, action: "activate-campaign" | "pause-campaign" | "resume-campaign" | "revoke-campaign", from: RedemptionCampaign["status"][], to: RedemptionCampaign["status"], nowMs: number) { this.authorize(operator, action, id, nowMs); const current = this.requireCampaign(id); if (!from.includes(current.status)) throw new RedemptionValidationError("Invalid campaign transition"); const next = { ...current, status: to }; this.campaigns.set(id, next); this.audit(operator.operatorId, action, id, "succeeded", `${current.status}->${to}`, nowMs); return next; }
  private authorize(operator: RedemptionOperatorContext, action: RedemptionAuditEvent["action"], target: string, nowMs: number) { if (operator.role !== "redemption-operator" || !operator.recentlyVerified) { this.audit(operator.operatorId, action, target, "rejected", "authorization", nowMs); throw new RedemptionAuthorizationError("Redemption operator authorization and recent verification required"); } }
  private validateCampaign(input: CreateCampaignInput) { for (const value of [input.pointsPerCode, input.codeLimit, input.pointsBudget]) if (!Number.isInteger(value) || value <= 0) throw new RedemptionValidationError("Campaign values must be positive integers"); if (input.pointsPerCode > this.policy.maxPointsPerCode || input.codeLimit > this.policy.maxCodeCount || input.pointsBudget > this.policy.maxPointsBudget || input.pointsBudget < input.pointsPerCode || input.pointsPerCode * input.codeLimit > input.pointsBudget || input.expiresAtMs <= input.startsAtMs) throw new RedemptionValidationError("Campaign exceeds policy or has an invalid activation window"); }
  private requireCampaign(id: string) { const value = this.campaigns.get(id); if (!value) throw new RedemptionValidationError("Campaign not found"); return value; }
  private campaignCodeCount(id: string) { return [...this.codesById.values()].filter(code => code.campaignId === id).length; }
  private fail(context: RedemptionRequestContext, prefixHash: string) { this.limiter.failure(context.userId!, context.riskSourceHash, prefixHash, context.requestedAtMs); }
  private finish(result: PointsRedemptionResult, context: RedemptionRequestContext, started: number, campaignId?: string) { const campaign = campaignId ? this.campaigns.get(campaignId) : undefined; this.observations.push({ outcome: result.outcome, latencyMs: Math.max(0, Date.now() - started), riskHash: this.safeRisk(context.riskSourceHash), ...(campaign ? { campaignBudget: { redeemed: campaign.redeemedPoints, total: campaign.pointsBudget } } : {}) }); return result; }
  private audit(actor: string, action: RedemptionAuditEvent["action"], targetId: string, result: RedemptionAuditEvent["result"], reason: string, nowMs: number) { this.auditTrail.push({ id: `audit-${++this.counter}`, action, actorHash: this.safeActor(actor), targetId, result, reason, createdAtMs: nowMs }); }
  private safeActor(value: string) { return createHmac("sha256", "audit-domain").update(value).digest("hex").slice(0, 16); }
  private safeRisk(value: string) { return createHmac("sha256", "metrics-risk-domain").update(value).digest("hex").slice(0, 16); }
  private prefixHash(value: string) { return createHmac("sha256", "risk-prefix-domain").update(value.slice(0, 6)).digest("hex").slice(0, 16); }
}
