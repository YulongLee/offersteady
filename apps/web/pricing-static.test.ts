import { describe, expect, it, vi } from "vitest";
import { readFileSync } from "node:fs";
import { publicPricing, loadProductionPricing, renderPricing, assertCurrentPricing } from "./pricing-static.mjs";

function fixture() {
  return { data: { billing: { catalog: [
    { id: "test-pass", displayName: "测试会员", kind: "time_pass", priceCents: 1234, catalogVersion: 2, durationDays: 2, knowledgeIndexAllowance: 1, published: true },
    { id: "test-points", displayName: "<script>测试</script>", kind: "points_pack", priceCents: 567, catalogVersion: 2, points: 321, published: true },
    { id: "hidden", published: false }
  ], rates: { catalogVersion: 2, answerPoints: 2, screenshotAnswerPoints: 3, writtenExamPoints: 4, realtimeMinutePoints: 6, knowledgeIndexMinimumPoints: 10, knowledgeIndexPointsPer1000Tokens: 2 },
  balance: 999, ledger: ["private"], orders: ["private"] }, account: { secret: "private" } } };
}
const template = '<main><!-- PRODUCTION_PRICING --></main>';
describe("production catalogue static rendering", () => {
  it("renders actual cents, durations, allowances and rates without user data or unpublished products", () => {
    const pricing = publicPricing(fixture());
    const html = renderPricing(template, pricing);
    expect(html).toContain("¥12.34");
    expect(html).toContain("¥5.67");
    expect(html).toContain("连续 48 小时");
    expect(html).toContain("321 积分");
    expect(html).toContain("知识材料索引额度 1 次");
    expect(html).toContain("6 积分/分钟");
    expect(html).toContain("4 积分/次，会员也需扣除入场积分");
    expect(html).toContain("每 5,000 Token 10 积分");
    expect(html).toContain("&lt;script&gt;");
    expect(html).not.toContain("<script>");
    expect(JSON.stringify(pricing)).not.toMatch(/private|secret|balance|ledger|orders|hidden/);
    expect(html).toContain('href="/app/billing"');
  });
  it("rejects missing, empty, duplicate, malformed and inconsistent published catalogues", () => {
    expect(() => publicPricing({})).toThrow();
    const empty = fixture(); empty.data.billing.catalog = [];
    expect(() => publicPricing(empty)).toThrow();
    for (const value of [-1, NaN, 12.3]) {
      const bad = fixture(); bad.data.billing.catalog[0].priceCents = value;
      expect(() => publicPricing(bad)).toThrow();
    }
    const duplicate = fixture(); duplicate.data.billing.catalog.push(duplicate.data.billing.catalog[0]);
    expect(() => publicPricing(duplicate)).toThrow();
    const invalid = fixture(); invalid.data.billing.rates.catalogVersion = 1;
    expect(() => publicPricing(invalid)).toThrow();
  });
  it("fails closed on network or HTTP errors instead of falling back", async () => {
    await expect(loadProductionPricing(vi.fn().mockRejectedValue(new Error("offline")))).rejects.toThrow("offline");
    await expect(loadProductionPricing(vi.fn().mockResolvedValue({ ok: false, status: 503 }))).rejects.toThrow("503");
    const fetcher = vi.fn().mockResolvedValue({ ok: true, json: async () => fixture() });
    expect((await loadProductionPricing(fetcher)).catalog).toHaveLength(2);
    expect(fetcher.mock.calls[0][1]).not.toHaveProperty("credentials");
    expect(fetcher.mock.calls[0][1].redirect).toBe("error");
  });
  it("requires a fresh exact catalogue at release and does not depend on source ordering", () => {
    const now = new Date("2026-09-08T01:00:00Z");
    const pricing = publicPricing(fixture());
    const html = renderPricing(template, pricing, now);
    expect(() => assertCurrentPricing(html, pricing, now)).not.toThrow();
    expect(() => assertCurrentPricing(html.replace("¥12.34", "¥0.01"), pricing, now)).toThrow("do not match");
    const reversed = fixture(); reversed.data.billing.catalog.reverse();
    expect(() => assertCurrentPricing(html, publicPricing(reversed), now)).not.toThrow();
    const changed = fixture(); changed.data.billing.catalog[0].priceCents = 9876;
    expect(() => assertCurrentPricing(html, publicPricing(changed), now)).toThrow("changed");
    expect(() => assertCurrentPricing(html, pricing, new Date(now.getTime() + 86400001))).toThrow("expired");
    expect(() => renderPricing("", pricing)).toThrow("marker");
  });
});
describe("approved four-page SEO scope", () => {
  const paths = ["index.html", "public/seo/pricing.html", "public/seo/realtime-interview.html", "public/seo/ai-interview-assistant.html"];
  it("keeps unique metadata, one H1, indexability and matching visible schema", () => {
    const titles = new Set<string>();
    const sitemap = readFileSync("public/sitemap.xml", "utf8");
    for (const path of paths) {
      const html = readFileSync(path, "utf8");
      expect(html.match(/<h1[ >]/g)).toHaveLength(1);
      const title = html.match(/<title>(.*?)<\/title>/)?.[1];
      expect(title).toBeTruthy(); titles.add(title!);
      expect(html).not.toMatch(/noindex|FAQPage|AggregateRating|HowTo/);
      const canonical = html.match(/rel="canonical" href="([^"]+)"/)?.[1];
      expect(sitemap).toContain("<loc>" + canonical + "</loc>");
    }
    expect(titles.size).toBe(4);
    expect((sitemap.match(/<loc>/g) ?? []).length).toBe(30);
  });
  it("keeps homepage product definition in initial and client HTML with unchanged Title/H1", () => {
    for (const path of ["index.html", "src/App.tsx"]) expect(readFileSync(path, "utf8")).toContain("面试稳是一款面向求职者的AI面试助手");
    expect(readFileSync("index.html", "utf8")).toContain("<h1>AI 面试助手，让你的经历更好表达。</h1>");
  });
  it("describes six realtime steps and links all seven existing technical cluster pages", () => {
    const realtime = readFileSync(paths[2], "utf8");
    for (const label of ["面试音频", "实时语音识别", "问题理解", "结合本场资料", "生成回答建议", "用户自行判断和表达"]) expect(realtime).toContain(label);
    const technical = readFileSync(paths[3], "utf8");
    for (const url of ["/guides/technical-interview", ...["llm", "rag", "ai-agent", "java-backend", "frontend", "algorithms"].map(x => "/interview-questions/" + x)]) expect(technical).toContain('href="' + url + '"');
    expect(technical).not.toContain("/guides/ai-interview-assistant-comparison");
  });
});
