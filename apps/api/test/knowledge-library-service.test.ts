import { describe, expect, it } from "vitest";
import { BillingService } from "../src/billing-service.js";
import { KnowledgeLibraryService, knowledgeIndexPoints, type TokenizerAdapter } from "../src/knowledge-library-service.js";

const tokenizer = (tokens: number): TokenizerAdapter => ({ version: "test-v1", count: text => text.trim() ? tokens : 0 });
const setup = (tokens = 3_000) => { const billing = new BillingService(); billing.grantWelcome("u1", true, 1); return { billing, library: new KnowledgeLibraryService(billing, tokenizer(tokens)) }; };
const add = (library: KnowledgeLibraryService, fingerprint = "hash") => { const collection = library.createCollection("u1", `资料-${fingerprint}`); return library.addDocument("u1", collection.id, { displayName: `${fingerprint}.md`, fileKind: "md", sizeBytes: 100, contentFingerprint: fingerprint }); };

describe("KnowledgeLibraryService", () => {
  it.each([[1, 200], [3_000, 200], [10_000, 200], [10_001, 220], [25_001, 520]])("prices %i Tokens at %i points", (tokens, points) => expect(knowledgeIndexPoints(tokens)).toBe(points));

  it("creates an empty collection for free and settles a server quote once", () => {
    const { billing, library } = setup(); const document = add(library); expect(billing.balance("u1")).toBe(200);
    const quote = library.quoteIndex("u1", document.id, "synthetic normalized text", 3); expect(quote).toMatchObject({ tokenCount: 3000, pointCost: 200, projectedBalance: 0, catalogVersion: 3 });
    library.startIndex("u1", quote.quoteId, "index-1", 4); library.startIndex("u1", quote.quoteId, "index-1", 5); expect(billing.balance("u1")).toBe(0);
    library.completeIndex("u1", "index-1", "安全摘要", 6); library.completeIndex("u1", "index-1", "安全摘要", 7); expect(billing.balance("u1")).toBe(0);
  });

  it("rejects empty text, expired quotes and changed document snapshots", () => {
    const empty = setup(0); const emptyDoc = add(empty.library, "empty"); expect(() => empty.library.quoteIndex("u1", emptyDoc.id, "  ", 2)).toThrowError(expect.objectContaining({ code: "invalid-file" }));
    const { library } = setup(); const doc = add(library, "expiry"); const quote = library.quoteIndex("u1", doc.id, "synthetic", 10); expect(() => library.startIndex("u1", quote.quoteId, "late", 10 + 16 * 60_000)).toThrowError(expect.objectContaining({ code: "quote-expired" }));
  });

  it("releases failed point-funded work", () => {
    const { billing, library } = setup(); const document = add(library, "failure"); const quote = library.quoteIndex("u1", document.id, "synthetic", 2); library.startIndex("u1", quote.quoteId, "failed", 3); expect(billing.balance("u1")).toBe(0); library.failIndex("u1", "failed", 4); expect(billing.balance("u1")).toBe(200);
  });

  it("uses two allowances for a long pass and falls back to points", () => {
    const billing = new BillingService(); billing.grantWelcome("u1", true, 1); const order = billing.createOrder("u1", "pass-15", "wechat", 2); billing.submitProof("u1", order.id, "proof", "tx"); billing.reviewOrder("payment-reviewer", order.id, true, 3); const library = new KnowledgeLibraryService(billing, tokenizer(3_000));
    for (let index = 1; index <= 2; index++) { const doc = add(library, `member-${index}`); const quote = library.quoteIndex("u1", doc.id, "synthetic", 4 + index); expect(quote.entitlementSource).toBe("pass_allowance"); library.startIndex("u1", quote.quoteId, `member-${index}`, 6 + index); library.completeIndex("u1", `member-${index}`, "safe", 8 + index); }
    const third = add(library, "member-3"); const quote = library.quoteIndex("u1", third.id, "synthetic", 20); expect(quote).toMatchObject({ entitlementSource: "points", pointCost: 200 });
  });

  it("preserves a confirmed legacy quote and ownership-safe deleted labels", () => {
    const { billing, library } = setup(); const document = add(library, "legacy"); const legacy = library.createLegacyQuote("u1", document.id, 20, 2); library.startIndex("u1", legacy.quoteId, "legacy-index", 3); expect(billing.balance("u1")).toBe(180);
    expect(() => library.listDocuments("u2", document.collectionId)).toThrowError(expect.objectContaining({ code: "forbidden" })); library.failIndex("u1", "legacy-index"); library.deleteDocument("u1", document.id); expect(library.historicalLabel("u1", document.id)).toEqual({ displayName: "legacy.md", version: "v1", deleted: true });
  });

  it("keeps normalized text and filenames out of quote and cost payloads", () => {
    const { library } = setup(); const document = add(library, "private-fingerprint"); const quote = library.quoteIndex("u1", document.id, "sensitive synthetic knowledge body", 2); const serialized = JSON.stringify(quote); expect(serialized).not.toContain("sensitive synthetic knowledge body"); expect(serialized).not.toContain(document.displayName); expect(serialized).toContain("tokenCount");
  });
});
