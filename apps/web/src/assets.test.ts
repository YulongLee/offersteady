import { describe, expect, it } from "vitest";
import { productAssets, resolveAsset } from "./assets";
describe("product asset resolver", () => {
  it("resolves public valid assets with accessible text", () => { const value = resolveAsset("brand.logo"); expect(value?.path).toBe("/assets/brand/logo.svg"); expect(value?.alt).toBeTruthy(); });
  it("rejects missing, expired and malformed-integrity assets", () => { expect(resolveAsset("missing")).toBeNull(); const base = productAssets.entries[0]!; expect(resolveAsset(base.id, 10, { version: 2, entries: [{ ...base, expiresAtMs: 9 }] })).toBeNull(); expect(resolveAsset(base.id, 1, { version: 2, entries: [{ ...base, sha256: "bad" }] })).toBeNull(); });
});
