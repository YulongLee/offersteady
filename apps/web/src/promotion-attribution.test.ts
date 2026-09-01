import { beforeEach, describe, expect, it, vi } from "vitest";

import { installPromotionQualification } from "./promotion-attribution";

describe("promotion visit qualification", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ data: { accepted: true } }), { status: 200 })));
    Object.defineProperty(document, "visibilityState", { configurable: true, value: "visible" });
    document.cookie = "offersteady_pq=; Max-Age=0; Path=/";
    window.sessionStorage.clear();
  });

  it("does not add a request for ordinary non-promotion visitors", () => {
    installPromotionQualification();
    vi.advanceTimersByTime(1_000);
    expect(fetch).not.toHaveBeenCalled();
  });

  it("sends one best-effort qualification after a promoted page stays visible", async () => {
    document.cookie = "offersteady_pq=1; Path=/";
    installPromotionQualification();
    await vi.advanceTimersByTimeAsync(900);
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(String(vi.mocked(fetch).mock.calls[0]?.[0])).toContain("/api/v1/promotion/qualify");
    expect(document.cookie).not.toContain("offersteady_pq=1");
  });
});
