// @vitest-environment jsdom
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { assertCurrentPricing, renderPricing } from "./pricing-static.mjs";

const site = "https://mianshiwen.cn";
const modified = "2026-09-12";
// A local before-snapshot can exercise the same assertions without replacing source files.
const fixtureRoot = process.env.CN_CORE_SEARCH_FIXTURE_ROOT;
const root = fixtureRoot
  ? resolve(fixtureRoot)
  : resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const source = (path: string) => readFileSync(resolve(root, path), "utf8");
const publicSource = (path: string) => source(`apps/web/public/${path}`);
const text = (node: Node | null) => node?.textContent?.replace(/\s+/g, " ").trim() ?? "";
const htmlDocument = (name: string) => new DOMParser().parseFromString(publicSource(`seo/${name}.html`), "text/html");
const technicalPaths = [
  "/guides/technical-interview",
  ...["java-backend", "frontend", "algorithms", "llm", "rag", "ai-agent"].map(name => `/interview-questions/${name}`),
];
const pages = [
  { name: "realtime-interview", path: "/features/realtime-interview", title: "实时面试辅助：语音识别与回答建议｜面试稳", h1: "实时面试辅助：从问题到回答建议" },
  { name: "ai-interview-assistant", path: "/features/ai-interview-assistant", title: "程序员面试助手：技术追问与回答思路｜面试稳", h1: "程序员面试助手，把技术思路讲清楚" },
  { name: "pricing", path: "/pricing", title: "AI面试助手价格与套餐｜面试稳", h1: "面试稳价格与套餐" },
  { name: "download", path: "/download", title: "电脑伴随程序下载与安装｜面试稳", h1: "面试稳 AI 面试助手下载与安装" },
];
const moneyAmount = /[¥￥]\s*\d|\b(?:CNY|RMB)\s*\d|\d+(?:\.\d{1,2})?\s*元/;
const syntheticPricing = {
  catalog: [{ id: "synthetic-navigation-only", displayName: "合成测试积分包", kind: "points_pack", priceCents: 1, catalogVersion: 1, points: 1 }],
  rates: { catalogVersion: 1, answerPoints: 1, screenshotAnswerPoints: 1, writtenExamPoints: 1, realtimeMinutePoints: 1, knowledgeIndexMinimumPoints: 1, knowledgeIndexPointsPer1000Tokens: 1 },
};

function expectPublicPricingAndPurchase(guidance: string) {
  expect(guidance).toMatch(/(?:公开|匿名|未登录|无需登录|不登录)[^。！？\n]{0,100}(?:\/pricing|价格|看价|查看)|(?:\/pricing|价格)[^。！？\n]{0,100}(?:公开|匿名|未登录|无需登录|不登录)/);
  expect(guidance).toMatch(/登录(?:后)?[^。！？\n]{0,60}(?:购买|下单|支付)|(?:购买|下单|支付)[^。！？\n]{0,60}(?:需|应|要)[^。！？\n]{0,8}登录/);
}

describe("CN core search pages: static delivery and preserved identity", () => {
  for (const page of pages) {
    it(`${page.path} preserves metadata and H1 without adding executable content`, () => {
      const doc = htmlDocument(page.name);
      expect(doc.querySelectorAll("title")).toHaveLength(1);
      expect(doc.querySelectorAll("h1")).toHaveLength(1);
      if (page.name === "download") {
        for (const heading of [doc.title, text(doc.querySelector("h1"))]) {
          expect(heading).toMatch(/面试稳/);
          expect(heading).toMatch(/下载/);
        }
      } else {
        expect(doc.title).toBe(page.title);
        expect(text(doc.querySelector("h1"))).toBe(page.h1);
      }
      expect(doc.querySelectorAll('link[rel="canonical"]')).toHaveLength(1);
      expect(doc.querySelector('link[rel="canonical"]')?.getAttribute("href")).toBe(site + page.path);
      expect(doc.querySelector('meta[property="og:url"]')?.getAttribute("content")).toBe(site + page.path);
      for (const selector of ['meta[name="description"]', 'meta[property="og:description"]', 'meta[name="twitter:description"]']) {
        expect(doc.querySelectorAll(selector)).toHaveLength(1);
        expect(doc.querySelector(selector)?.getAttribute("content")?.trim().length).toBeGreaterThan(15);
      }
      for (const meta of doc.querySelectorAll('meta[name="robots"], meta[name="googlebot"], meta[name="baiduspider"]')) {
        expect(meta.getAttribute("content")).not.toMatch(/noindex|none/i);
      }
      expect(doc.querySelectorAll('script:not([type="application/ld+json"]), script[src]')).toHaveLength(0);
      for (const element of doc.querySelectorAll("*")) {
        expect(Array.from(element.attributes).filter(attribute => /^on/i.test(attribute.name))).toHaveLength(0);
      }
      for (const anchor of doc.querySelectorAll("a[href]")) expect(anchor.getAttribute("href")).not.toMatch(/^\s*javascript:/i);
    });

    it(`${page.path} has dated WebPage/BreadcrumbList JSON-LD allowed by its exact CSP hash`, () => {
      const doc = htmlDocument(page.name);
      const scripts = Array.from(doc.querySelectorAll('script[type="application/ld+json"]'));
      expect(scripts).toHaveLength(1);
      const data = JSON.parse(scripts[0].textContent ?? "");
      expect(data["@context"]).toBe("https://schema.org");
      const graph = data["@graph"] as Array<Record<string, unknown>>;
      expect(graph.map(node => node["@type"]).sort()).toEqual(["BreadcrumbList", "WebPage"]);
      expect(graph.find(node => node["@type"] === "WebPage")).toMatchObject({
        "@id": `${site}${page.path}#webpage`, url: site + page.path, dateModified: modified, inLanguage: "zh-CN",
      });
      const breadcrumb = graph.find(node => node["@type"] === "BreadcrumbList");
      expect(breadcrumb?.itemListElement).toEqual([
        expect.objectContaining({ "@type": "ListItem", position: 1, item: `${site}/` }),
        expect.objectContaining({ "@type": "ListItem", position: 2, item: site + page.path }),
      ]);
      const scriptPolicy = source("infra/nginx/default.conf").match(/script-src\s+([^;]+);/)?.[1] ?? "";
      const hash = createHash("sha256").update(scripts[0].textContent ?? "", "utf8").digest("base64");
      expect(scriptPolicy.split(/\s+/)).toContain(`'sha256-${hash}'`);
      expect(scriptPolicy).not.toMatch(/unsafe-inline|unsafe-eval|\*/);
    });

    it(`${page.path} exposes dated, navigable sections within the source HTML budget`, () => {
      const doc = htmlDocument(page.name);
      expect(doc.body.classList.contains("conversion-page")).toBe(true);
      const date = doc.querySelector(`main time[datetime="${modified}"]`);
      expect(date).not.toBeNull();
      expect(text(date)).toMatch(/2026(?:-|年)0?9(?:-|月)12/);
      expect(date?.closest('[hidden], [aria-hidden="true"]')).toBeNull();
      // The pricing catalogue's target is emitted by the existing pure build renderer.
      const navigationDoc = page.name === "pricing"
        ? new DOMParser().parseFromString(renderPricing(publicSource("seo/pricing.html"), syntheticPricing, new Date(`${modified}T00:00:00Z`)), "text/html")
        : doc;
      const toc = navigationDoc.querySelector('nav[aria-label="本页目录"]');
      expect(toc).not.toBeNull();
      const links = Array.from(toc?.querySelectorAll('a[href^="#"]') ?? []);
      expect(links.length).toBeGreaterThanOrEqual(3);
      const ids = Array.from(navigationDoc.querySelectorAll("[id]")).map(node => node.id);
      expect(new Set(ids).size).toBe(ids.length);
      for (const link of links) {
        expect(text(link).length).toBeGreaterThan(0);
        const id = decodeURIComponent(link.getAttribute("href")!.slice(1));
        const section = navigationDoc.getElementById(id);
        expect(section, `Missing section for ${page.path}#${id}`).not.toBeNull();
        expect(section?.closest("main")).not.toBeNull();
        expect(section?.matches("h2, h3") || !!section?.querySelector("h2, h3")).toBe(true);
      }
      expect(Buffer.byteLength(publicSource(`seo/${page.name}.html`), "utf8")).toBeLessThanOrEqual(12000);
    });
  }

  it("keeps titles and descriptions distinct across the four search intents", () => {
    const documents = pages.map(page => htmlDocument(page.name));
    expect(new Set(documents.map(doc => doc.title)).size).toBe(4);
    expect(new Set(documents.map(doc => doc.querySelector('meta[name="description"]')?.getAttribute("content"))).size).toBe(4);
  });
});

describe("CN core search pages: useful scenarios and conversion paths", () => {
  for (const name of ["realtime-interview", "ai-interview-assistant"]) {
    it(`${name} explains selected materials and correction, with a labelled synthetic example`, () => {
      const doc = htmlDocument(name);
      const blocks = Array.from(doc.querySelectorAll("main p, main li")).map(text);
      expect(blocks.some(block => /简历/.test(block) && /经历|项目|负责/.test(block))).toBe(true);
      expect(blocks.some(block => /JD/i.test(block) && /岗位|要求|职责|目标/.test(block))).toBe(true);
      expect(blocks.some(block => /知识(?:资料|材料)/.test(block) && /选择|参考|解释|原理|补充|提供/.test(block))).toBe(true);
      expect(blocks.some(block => /识别|转写/.test(block) && /错误|有误|错|不准/.test(block) && /核对|手动|纠正|补充/.test(block))).toBe(true);
      expect(blocks.some(block => /(?:你|自己|自行|用户)[^。！？]{0,40}(?:核实|核对)|(?:核实|核对)[^。！？]{0,40}(?:自己|自行)/.test(block))).toBe(true);
      const examples = Array.from(doc.querySelectorAll("section, figure, aside"))
        .filter(node => /合成说明示例/.test(text(node)))
        .sort((a, b) => text(a).length - text(b).length);
      expect(examples.length).toBeGreaterThan(0);
      expect(text(examples[0])).toMatch(/问题|追问|提问/);
      expect(text(examples[0])).toMatch(/建议|回答思路/);
      expect(text(examples[0])).toMatch(/核实|核对/);
    });
  }

  it("keeps all seven technical cluster links in the programmer page's main content", () => {
    const doc = htmlDocument("ai-interview-assistant");
    for (const path of technicalPaths) {
      const link = doc.querySelector(`main a[href="${path}"]`);
      expect(link, path).not.toBeNull();
      expect(text(link).length).toBeGreaterThan(2);
    }
  });

  it("retains the production pricing generation marker without source RMB amounts", () => {
    const html = publicSource("seo/pricing.html");
    expect(html.match(/<!--\s*PRODUCTION_PRICING\s*-->/g)).toHaveLength(1);
    expect(html).not.toMatch(moneyAmount);
    expect(htmlDocument("pricing").querySelector('a[href="/guide#billing"]')).not.toBeNull();
  });

  it("does not let the editorial update date replace the generated catalogue's freshness timestamp", () => {
    const builtAt = new Date("2026-09-13T12:00:00Z");
    const html = renderPricing(publicSource("seo/pricing.html"), syntheticPricing, builtAt);
    expect(() => assertCurrentPricing(html, syntheticPricing, builtAt)).not.toThrow();
  });

  it("answers anonymous price viewing versus signed-in purchasing in a visible FAQ", () => {
    const doc = htmlDocument("pricing");
    const faq = Array.from(doc.querySelectorAll("main section"))
      .find(section => Array.from(section.querySelectorAll("h2, h3, summary")).some(heading => /登录/.test(text(heading))));
    expect(faq).toBeDefined();
    expectPublicPricingAndPurchase(text(faq ?? null));
  });

  it("sends the primary download action to the existing homepage without requiring login", () => {
    const doc = htmlDocument("download");
    const primary = doc.querySelector(".hero-actions a.primary");
    expect(primary?.getAttribute("href")).toBe("/");
    expect(text(primary)).toBe("到首页下载 Windows / macOS");
    for (const link of doc.querySelectorAll('a[href="/login"], a[href^="/login?"]')) {
      expect(text(link)).not.toMatch(/下载/);
    }
  });
});

describe("CN machine-readable public facts", () => {
  for (const file of ["llms.txt", "llms-full.txt", "public-facts.json"]) {
    it(`${file} directs anonymous readers to public pricing and reserves login for purchasing`, () => {
      const raw = publicSource(file);
      const guidance = file.endsWith(".json") ? JSON.parse(raw).dynamicFacts.pricing : raw;
      expect(guidance).toContain("/pricing");
      expectPublicPricingAndPurchase(guidance);
      expect(guidance).not.toMatch(/(?:价格|商品)[^。\n]{0,50}(?:应|请)?以登录后的(?:实时页面|积分与会员页面|“积分与会员”页面)为准/);
      expect(guidance).not.toMatch(moneyAmount);
      if (!file.endsWith(".json")) {
        const technical = raw.split(/\n\s*\n/).find(paragraph => paragraph.includes("/features/ai-interview-assistant"));
        expect(technical).toMatch(/程序员|技术岗位|技术面试/);
      }
    });
  }

  it("preserves schema 1.1 fields, verified identity and safety boundaries while dating current facts", () => {
    const facts = JSON.parse(publicSource("public-facts.json"));
    expect(Object.keys(facts)).toEqual(expect.arrayContaining([
      "schemaVersion", "lastUpdated", "canonicalSite", "product", "capabilities", "inputMethods", "dataBoundaries",
      "dynamicFacts", "officialPages", "maintainedGuides", "technicalTopics", "contentHubs", "entityBoundaries", "contact",
    ]));
    expect(facts).toMatchObject({ schemaVersion: "1.1", lastUpdated: modified, canonicalSite: `${site}/` });
    expect(Object.keys(facts.product)).toEqual(expect.arrayContaining(["name", "alternateName", "operatorLabel", "category", "languages", "surfaces", "summary"]));
    expect(facts.product).toMatchObject({ name: "面试稳AI助手", alternateName: "面试稳", operatorLabel: "OneShow AI Lab", languages: ["zh-CN"] });
    expect(facts.dataBoundaries).toEqual({ rawAudioStoredByDefault: false, aiOutputIsReferenceOnly: true, guaranteesInterviewOutcome: false, detailsUrl: `${site}/privacy` });
    expect(facts.entityBoundaries).toEqual({ productNameVerified: true, publicTeamLabel: "OneShow AI Lab", registeredLegalOperatorVerified: false, platformNamesIndicateAffiliation: false });
    expect(Object.keys(facts.dynamicFacts)).toEqual(expect.arrayContaining(["pricing", "paymentChannels", "desktopDownloads"]));
    expect(facts.officialPages.pricing).toBe(`${site}/pricing`);
    expect(Object.keys(facts.officialPages)).toEqual(expect.arrayContaining(["homepage", "guide", "features", "interviewQuestions", "guides", "pricing", "download", "security", "about", "contact", "privacy", "terms", "llms", "llmsFull"]));
    expect(Object.keys(facts.contact)).toEqual(expect.arrayContaining(["email", "filingNumber", "filingUrl", "publicSecurityFilingNumber", "publicSecurityFilingUrl"]));
    expect(facts.capabilities.map((capability: { id: string }) => capability.id)).toEqual(expect.arrayContaining(["interview-preparation", "realtime-interview", "screenshot-answer", "interview-review"]));
    expect(facts.technicalTopics).toEqual(expect.arrayContaining(technicalPaths.filter(path => path.startsWith("/interview-questions/")).map(path => site + path)));
  });
});

describe("CN discovery set and shared style budget", () => {
  const sitemap = () => new DOMParser().parseFromString(publicSource("sitemap.xml"), "application/xml");

  it("keeps the exact existing set of 30 sitemap URLs", () => {
    const doc = sitemap();
    expect(doc.querySelector("parsererror")).toBeNull();
    const paths = ["/", "/guide", "/features", "/interview-questions", "/guides", "/pricing", "/download", "/security", "/about", "/contact",
      ...["ai-interview-assistant", "realtime-interview", "screenshot-answer", "interview-review"].map(name => `/features/${name}`),
      ...["audio-troubleshooting", "interview-preparation", "macos-permissions", "feishu-audio-setup", "tencent-meeting-audio-setup", "star-interview-answer", "self-introduction", "project-experience", "technical-interview", "common-interview-questions"].map(name => `/guides/${name}`),
      ...technicalPaths.filter(path => path.startsWith("/interview-questions/")),
    ];
    const urls = Array.from(doc.querySelectorAll("url > loc")).map(text);
    expect(urls).toHaveLength(30);
    expect(urls.sort()).toEqual(paths.map(path => site + path).sort());
  });

  it("updates only the four edited pages' lastmod while keeping the homepage and other dates", () => {
    const changed = new Set(pages.map(page => site + page.path));
    for (const entry of sitemap().querySelectorAll("url")) {
      const url = text(entry.querySelector("loc"));
      const expected = changed.has(url) ? modified : url === `${site}/` ? "2026-09-08" : "2026-08-19";
      expect(text(entry.querySelector("lastmod")), url).toBe(expected);
    }
  });

  it("keeps the shared stylesheet within 8 KiB with scoped focus and reduced-motion support", () => {
    const css = publicSource("seo/public-search.css");
    expect(Buffer.byteLength(css, "utf8")).toBeLessThanOrEqual(8000);
    expect(css).toMatch(/\.conversion-page[^{}]*:focus-visible\s*\{[^}]*outline\s*:/s);
    expect(css).toMatch(/prefers-reduced-motion\s*:\s*reduce/);
  });
});
