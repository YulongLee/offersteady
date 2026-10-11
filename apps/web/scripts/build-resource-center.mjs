import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { resourceCenterManifest, resourceReviewDate } from "../resource-center-manifest.mjs";

const webRoot = resolve(import.meta.dirname, "..");
const contentRoot = resolve(webRoot, "../../content/cn-resource-center-20261011");
const outputRoot = resolve(webRoot, "public/resources");
const origin = "https://mianshiwen.cn";
const shareCard = `${origin}/assets/brand/share-card.png`;

const escapeHtml = value => String(value)
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;");

const inline = value => {
  let html = escapeHtml(value);
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
  html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/\[([^\]]+)\]\((https?:\/\/[^)]+|\/[^)]+)\)/g, (_, label, href) => `<a href="${href}"${href.startsWith("http") ? ' rel="noreferrer"' : ""}>${label}</a>`);
  return html;
};

const isTableRow = line => line.trim().startsWith("|") && line.trim().endsWith("|");
const tableCells = line => line.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map(cell => inline(cell.trim()));

function renderMarkdown(source) {
  const lines = source.split(/\r?\n/);
  const body = [];
  let paragraph = [];
  let listType = null;
  let table = null;
  let skipSection = false;

  const flushParagraph = () => {
    if (paragraph.length) body.push(`<p>${inline(paragraph.join(" "))}</p>`);
    paragraph = [];
  };
  const flushList = () => {
    if (!listType) return;
    body.push(`</${listType}>`);
    listType = null;
  };
  const flushTable = () => {
    if (!table) return;
    const [header, ...rows] = table;
    body.push(`<table class="data-table"><thead><tr>${header.map(cell => `<th>${cell}</th>`).join("")}</tr></thead><tbody>${rows.map(row => `<tr>${row.map(cell => `<td>${cell}</td>`).join("")}</tr>`).join("")}</tbody></table>`);
    table = null;
  };

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line) {
      flushParagraph(); flushList(); flushTable();
      continue;
    }
    if (/^## (配图建议|内链计划)$/.test(line)) {
      flushParagraph(); flushList(); flushTable(); skipSection = true; continue;
    }
    if (skipSection && /^## /.test(line)) skipSection = false;
    if (skipSection) continue;
    if (/^(Meta Title|Meta Description|URL Slug|主关键词|相关关键词)[:：]/.test(line)) continue;
    if (/^# /.test(line)) continue;
    if (/^## /.test(line)) { flushParagraph(); flushList(); flushTable(); body.push(`<h2>${inline(line.slice(3))}</h2>`); continue; }
    if (/^### /.test(line)) { flushParagraph(); flushList(); flushTable(); body.push(`<h3>${inline(line.slice(4))}</h3>`); continue; }
    if (/^#### /.test(line)) { flushParagraph(); flushList(); flushTable(); body.push(`<h4>${inline(line.slice(5))}</h4>`); continue; }
    if (isTableRow(line)) {
      flushParagraph(); flushList();
      if (/^\|[\s|:-]+\|$/.test(line)) continue;
      table ??= [];
      table.push(tableCells(line));
      continue;
    }
    const unordered = line.match(/^-\s+(.*)$/);
    const ordered = line.match(/^\d+\.\s+(.*)$/);
    if (unordered || ordered) {
      flushParagraph(); flushTable();
      const nextType = unordered ? "ul" : "ol";
      if (listType !== nextType) { flushList(); body.push(`<${nextType}>`); listType = nextType; }
      body.push(`<li>${inline((unordered ?? ordered)[1])}</li>`);
      continue;
    }
    flushList(); flushTable(); paragraph.push(line);
  }
  flushParagraph(); flushList(); flushTable();
  return body.join("\n").replaceAll("<section class=\"article-section\"><h2", "<section class=\"article-section\"><h2");
}

const nav = `<header class="site-header shell"><a class="brand" href="/"><img src="/assets/brand/app-icon.svg" width="42" height="42" alt="" />面试稳AI助手</a><nav class="site-nav" aria-label="公开导航"><a href="/features">产品功能</a><a href="/interview-questions">面试题与专题</a><a href="/guides">面试指南</a><a href="/resources/">技术报告</a><a href="/login">登录</a></nav></header>`;
const footer = `<footer class="page-footer"><div class="shell"><nav><a href="/">首页</a><a href="/features">产品功能</a><a href="/interview-questions">面试题与专题</a><a href="/guides">面试指南</a><a href="/resources/">技术报告</a><a href="/guide">使用手册</a><a href="/privacy">隐私政策</a></nav><small>© 2026 面试稳AI助手 · 技术内容用于理解和准备，不代表特定公司的官方题库。</small></div></footer>`;

function jsonLd(item, url, type = "Article", wordCount) {
  const pageTitle = item?.title ?? "技术报告与资源中心";
  const pageDescription = item?.description ?? "面试稳技术报告与资源中心，收录公开技术排查方法。";
  const page = {
    "@type": type,
    "@id": `${origin}${url}#${type === "Article" ? "article" : "webpage"}`,
    headline: pageTitle,
    name: pageTitle,
    description: pageDescription,
    inLanguage: "zh-CN",
    mainEntityOfPage: `${origin}${url}`,
    author: { "@type": "Organization", name: "面试稳产品与支持团队" },
    publisher: { "@id": `${origin}/#organization` },
    datePublished: resourceReviewDate,
    dateModified: resourceReviewDate,
  };
  if (type === "Article" && item) {
    page.articleSection = item.category;
    page.keywords = item.keywords;
    page.image = [shareCard];
    page.isAccessibleForFree = true;
    if (wordCount) page.wordCount = wordCount;
  }
  const graph = [page];
  if (type === "CollectionPage") {
    page.mainEntity = { "@id": `${origin}${url}#item-list` };
    graph.push({
      "@type": "ItemList",
      "@id": `${origin}${url}#item-list`,
      name: "面试稳技术报告列表",
      numberOfItems: resourceCenterManifest.length,
      itemListElement: resourceCenterManifest.map((entry, index) => ({
        "@type": "ListItem",
        position: index + 1,
        name: entry.title,
        url: `${origin}/resources/${entry.slug}/`,
        description: entry.summary,
      })),
    });
  }
  graph.push({ "@type": "BreadcrumbList", itemListElement: [{ "@type": "ListItem", position: 1, name: "面试稳AI助手", item: `${origin}/` }, { "@type": "ListItem", position: 2, name: "技术报告与资源中心", item: `${origin}/resources/` }, ...(item && type !== "CollectionPage" ? [{ "@type": "ListItem", position: 3, name: item.title, item: `${origin}${url}` }] : [])] });
  return JSON.stringify({ "@context": "https://schema.org", "@graph": graph });
}

function document({ title, description, url, eyebrow, h1, lede, body, schema, item }) {
  const articleMeta = item ? `<meta name="author" content="面试稳产品与支持团队" /><meta property="article:section" content="${escapeHtml(item.category)}" /><meta property="article:published_time" content="${resourceReviewDate}" /><meta property="article:modified_time" content="${resourceReviewDate}" />` : "";
  const metaItems = item
    ? `<span>发布与复核：<time datetime="${resourceReviewDate}">${resourceReviewDate}</time></span><span>${escapeHtml(item.category)}</span><span>${escapeHtml(item.readingTime)}</span>`
    : `<span>发布与复核：<time datetime="${resourceReviewDate}">${resourceReviewDate}</time></span><span>复核：面试稳产品与支持团队</span><span>公开技术整理</span>`;
  return `<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8" /><meta name="viewport" content="width=device-width, initial-scale=1.0" /><meta name="theme-color" content="#071019" /><meta name="robots" content="index,follow,max-image-preview:large" /><link rel="icon" href="/assets/brand/favicon.png" type="image/png" /><link rel="stylesheet" href="/seo/public-search.css" /><link rel="canonical" href="${origin}${url}" /><meta name="description" content="${escapeHtml(description)}" />${articleMeta}<meta property="og:type" content="${url === "/resources/" ? "website" : "article"}" /><meta property="og:site_name" content="面试稳AI助手" /><meta property="og:locale" content="zh_CN" /><meta property="og:url" content="${origin}${url}" /><meta property="og:title" content="${escapeHtml(title)}" /><meta property="og:description" content="${escapeHtml(description)}" /><meta property="og:image" content="${shareCard}" /><meta property="og:image:width" content="1200" /><meta property="og:image:height" content="630" /><meta property="og:image:alt" content="面试稳技术报告与资源中心" /><meta name="twitter:card" content="summary_large_image" /><meta name="twitter:title" content="${escapeHtml(title)}" /><meta name="twitter:description" content="${escapeHtml(description)}" /><meta name="twitter:image" content="${shareCard}" /><title>${escapeHtml(title)}</title><script type="application/ld+json">${schema}</script></head><body class="conversion-page">${nav}<main class="shell"><article><header class="hero"><p class="eyebrow">${escapeHtml(eyebrow)}</p><h1>${escapeHtml(h1)}</h1><p class="lede">${escapeHtml(lede)}</p><div class="meta-strip">${metaItems}</div></header>${body}</article></main>${footer}</body></html>`;
}

const relatedResources = item => item.relatedSlugs.map(slug => resourceCenterManifest.find(entry => entry.slug === slug)).filter(Boolean).map(entry => `<article class="decision-card"><p class="eyebrow">${escapeHtml(entry.category)}</p><h3><a href="/resources/${entry.slug}/">${escapeHtml(entry.title)}</a></h3><p>${escapeHtml(entry.summary)}</p></article>`).join("");

await mkdir(outputRoot, { recursive: true });
const cards = resourceCenterManifest.map(item => `<article class="decision-card"><p class="eyebrow">${escapeHtml(item.category)}</p><h2><a href="/resources/${item.slug}/">${escapeHtml(item.title)}</a></h2><p>${escapeHtml(item.summary)}</p><a class="text-link" href="/resources/${item.slug}/">阅读报告 ↗</a></article>`).join("");
const directoryBody = `<div class="content-grid"><div><section class="article-section"><h2>首批技术报告</h2><p>这里收录面试稳团队整理的公开技术报告，优先回答用户在面试准备、资料处理、设备连接和实时链路中经常遇到的问题。文章使用合成示例，不包含用户简历、面试录音、真实日志或服务密钥。</p><div class="decision-grid">${cards}</div></section><section class="article-section"><h2>按问题选择排查路径</h2><ol><li>接口延迟或请求量异常：先看 <a href="/resources/api-p95-latency-diagnosis/">API P95 长尾拆解</a>，再对照 <a href="/resources/realtime-interview-polling/">轮询与状态同步</a>。</li><li>面试结束后内存不降：先区分 RSS 与活跃对象，再看 <a href="/resources/container-memory-not-falling/">容器内存排查</a>。</li><li>资料或设备不可用：分别查看 <a href="/resources/resume-pdf-parsing-failures/">PDF 解析</a> 和 <a href="/resources/mac-microphone-permission/">Mac 麦克风权限</a>。</li></ol><p>需要产品操作时，再进入对应的<a href="/guides">面试指南</a>、<a href="/features/realtime-interview">实时面试辅助</a>或<a href="/download">下载说明</a>。</p><p class="boundary"><strong>内容边界：</strong>技术报告用于理解和排查，不构成线上 SLA、面试结果保证或对特定招聘流程的承诺。</p></section><section class="article-section source-note"><h2>更新说明</h2><p>本目录首批内容于 ${resourceReviewDate} 发布与复核。产品功能、价格和权限以对应公开页面和登录后实时信息为准。</p></section></div><aside class="side-card"><h2>继续了解</h2><ul><li><a href="/guides">面试指南</a></li><li><a href="/features/ai-interview-assistant">程序员与技术岗位场景</a></li><li><a href="/features/realtime-interview">实时面试辅助</a></li><li><a href="/security">安全与隐私</a></li><li><a href="/login">用真实资料开始准备</a></li></ul></aside></div>`;
await writeFile(resolve(outputRoot, "index.html"), document({ title: "技术报告与资源中心｜面试稳AI助手", description: "面试稳技术报告与资源中心，整理 API P95、容器内存、PDF 简历解析、Mac 麦克风权限和实时面试轮询等问题的公开排查方法，适合面试准备与产品使用排障。", url: "/resources/", eyebrow: "RESOURCE CENTER", h1: "技术报告与资源中心", lede: "从面试准备、资料处理到实时链路，把常见问题拆成可验证、可执行的排查步骤。", body: directoryBody, schema: jsonLd({ title: "技术报告与资源中心", description: "面试稳技术报告与资源中心，收录公开技术排查方法。" }, "/resources/", "CollectionPage") }), "utf8");

for (const item of resourceCenterManifest) {
  const source = await readFile(resolve(contentRoot, `${item.slug}.md`), "utf8");
  const textForCount = source.replace(/^#.*$/gm, "").replace(/^(Meta Title|Meta Description|URL Slug|主关键词|相关关键词)[:：].*$/gm, "").replace(/## (配图建议|内链计划)[\s\S]*$/m, "");
  const wordCount = (textForCount.match(/[A-Za-z0-9]+|[\u4e00-\u9fff]/g) ?? []).length;
  const related = relatedResources(item);
  const body = `<div class="content-grid"><div>${renderMarkdown(source)}<p class="boundary"><strong>内容边界：</strong>本文用于公开技术理解与排查，示例为合成说明，不代表线上 SLA、面试结果或特定公司官方题库。</p><section class="article-section"><h2>相关技术报告</h2><div class="decision-grid">${related}</div></section></div><aside class="side-card"><h2>继续了解</h2><ul><li><a href="/resources/">返回资源中心</a></li><li><a href="/features/realtime-interview">实时面试辅助</a></li><li><a href="/guides/technical-interview">技术面试准备</a></li><li><a href="/guides/interview-preparation">面试准备清单</a></li><li><a href="/security">安全与隐私</a></li></ul></aside></div>`;
  await mkdir(resolve(outputRoot, item.slug), { recursive: true });
  await writeFile(resolve(outputRoot, item.slug, "index.html"), document({ title: item.metaTitle, description: item.description, url: `/resources/${item.slug}/`, eyebrow: item.eyebrow, h1: item.title, lede: item.summary, body, item, schema: jsonLd(item, `/resources/${item.slug}/`, "Article", wordCount) }), "utf8");
}

console.log(`Generated resource center: ${resourceCenterManifest.length} reports + directory`);
