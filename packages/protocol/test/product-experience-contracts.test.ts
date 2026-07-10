import { describe, expect, it } from "vitest";
import type { BillingProduct, DesktopReleaseManifest, KnowledgeDocumentVersion, KnowledgeIndexQuote, SafeAccountSummary, TimePassEntitlement, UsageRates } from "../src/index";

describe("product experience contracts", () => {
  it("serializes safe identity without provider secrets", () => {
    const account: SafeAccountSummary = { id: "u1", displayName: "微信用户", createdAtMs: 1, bindings: [{ id: "b1", provider: "wechat", displayName: "微信账号", status: "active", boundAtMs: 1, canUnbind: false }] };
    const serialized = JSON.stringify(account);
    expect(serialized).toContain("微信账号"); expect(serialized).not.toMatch(/secret|token|subjectId/i);
  });

  it("preserves document version and knowledge pricing", () => {
    const document: KnowledgeDocumentVersion = { id: "d1", collectionId: "c1", ownerUserId: "u1", displayName: "notes.md", fileKind: "md", sizeBytes: 100, contentFingerprint: "hash", version: 2, status: "pending", createdAtMs: 1 };
    const rates: UsageRates = { catalogVersion: 4, answerPoints: 5, screenshotAnswerPoints: 15, knowledgeIndexMinimumPoints: 20, knowledgeIndexPointsPer1000Tokens: 4, tokenizerVersion: "synthetic-v1" };
    expect(JSON.parse(JSON.stringify(document)).version).toBe(2); expect(rates.knowledgeIndexMinimumPoints).toBe(20);
  });

  it("keeps platform architecture and verification state in the manifest", () => {
    const manifest: DesktopReleaseManifest = { version: 1, generatedAtMs: 1, entries: [{ id: "mac-arm", platform: "macos", architecture: "arm64", displayName: "macOS Apple Silicon", version: "0.1.0", minimumOs: "14.2", fileSizeBytes: 10, sha256: "a".repeat(64), signingStatus: "verified", notarized: true, publishedAtMs: 1, protocolVersion: "1.0.0", downloadUrl: "/mac.dmg", capabilities: { microphone: true, systemAudio: true, manualInputFallback: true, screenshotFallback: true } }] };
    expect(manifest.entries[0]).toMatchObject({ architecture: "arm64", signingStatus: "verified" });
  });

  it("preserves versioned knowledge quotes and pass allowances", () => {
    const product: BillingProduct = { id: "pass-15", catalogVersion: 3, kind: "time_pass", displayName: "15 天会员", priceCents: 21990, durationDays: 15, knowledgeIndexAllowance: 2, published: true };
    const entitlement: TimePassEntitlement = { id: "e1", userId: "u1", productId: product.id, startsAtMs: 1, endsAtMs: 2, orderId: "o1", knowledgeAllowanceGranted: 2, knowledgeAllowanceUsed: 0, knowledgeAllowanceLocked: 0 };
    const quote: KnowledgeIndexQuote = { quoteId: "q1", documentVersionId: "d1", contentFingerprint: "synthetic", tokenCount: 10_001, billableUnits: 3, pointCost: 60, entitlementSource: "points", allowanceRemaining: 0, catalogVersion: 4, tokenizerVersion: "test-v1", createdAtMs: 1, expiresAtMs: 2, requiresConfirmation: true, projectedBalance: 80 };
    expect(JSON.parse(JSON.stringify({ product, entitlement, quote }))).toMatchObject({ product: { knowledgeIndexAllowance: 2 }, quote: { tokenCount: 10_001, pointCost: 60 } });
  });
});
