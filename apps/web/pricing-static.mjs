import { createHash } from "node:crypto";

export const catalogSource = "https://mianshiwen.cn/api/v1/web/state";
const rateKeys = ["catalogVersion", "answerPoints", "screenshotAnswerPoints", "writtenExamPoints", "realtimeMinutePoints", "knowledgeIndexMinimumPoints", "knowledgeIndexPointsPer1000Tokens"];
const integer = (value, min = 0) => Number.isSafeInteger(value) && value >= min;
const escapeHtml = value => String(value).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

export function publicPricing(envelope) {
  const billing = envelope?.data?.billing;
  if (!Array.isArray(billing?.catalog) || !billing.rates) throw new Error("Missing production billing catalogue");
  const catalog = billing.catalog.filter(p => p.published === true).map(p => {
    if (!p.id || typeof p.id !== "string" || typeof p.displayName !== "string" || !p.displayName.trim()
      || !integer(p.priceCents, 1) || !integer(p.catalogVersion, 1)
      || !["time_pass", "points_pack"].includes(p.kind)
      || (p.kind === "time_pass" && (!integer(p.durationDays, 1) || !integer(p.knowledgeIndexAllowance)))
      || (p.kind === "points_pack" && !integer(p.points, 1))) throw new Error("Invalid published production product");
    return { id: p.id, displayName: p.displayName, kind: p.kind, priceCents: p.priceCents, catalogVersion: p.catalogVersion,
      ...(p.kind === "time_pass" ? { durationDays: p.durationDays, knowledgeIndexAllowance: p.knowledgeIndexAllowance } : { points: p.points }) };
  }).sort((a, b) => a.id.localeCompare(b.id));
  if (!catalog.length || new Set(catalog.map(p => p.id)).size !== catalog.length) throw new Error("Empty or duplicate production catalogue");
  const rates = Object.fromEntries(rateKeys.map(k => {
    if (!integer(billing.rates[k], 1)) throw new Error("Invalid production billing rates");
    return [k, billing.rates[k]];
  }));
  if (catalog.some(p => p.catalogVersion > rates.catalogVersion)) throw new Error("Inconsistent catalogue version");
  return { catalog, rates };
}

export async function loadProductionPricing(fetcher = fetch) {
  const response = await fetcher(catalogSource, { signal: AbortSignal.timeout(20000), redirect: "error", headers: { Accept: "application/json", "Cache-Control": "no-cache" } });
  if (!response.ok) throw new Error("Production pricing request failed: " + response.status);
  return publicPricing(await response.json());
}

export function pricingFingerprint(pricing) {
  return createHash("sha256").update(JSON.stringify(pricing)).digest("hex");
}

export function renderPricing(template, pricing, now = new Date()) {
  const marker = "<!-- PRODUCTION_PRICING -->";
  if (template.split(marker).length !== 2) throw new Error("Pricing template must have exactly one catalogue marker");
  const { catalog, rates } = pricing;
  const rows = kind => catalog.filter(p => p.kind === kind).sort((a, b) => a.priceCents - b.priceCents).map(p => {
    const benefit = p.kind === "time_pass"
      ? "会员期内实时面试、回答和截图不扣积分；知识材料索引额度 " + p.knowledgeIndexAllowance + " 次"
      : p.points + " 积分，按实际功能消耗";
    return '<tr data-product-id="' + escapeHtml(p.id) + '" data-price-cents="' + p.priceCents + '"><th scope="row">' + escapeHtml(p.displayName) + '</th><td data-label="价格">¥' + (p.priceCents / 100).toFixed(2) + '</td><td data-label="有效期">' + (p.kind === "time_pass" ? p.durationDays + " 天（连续 " + p.durationDays * 24 + " 小时）" : "余额长期保留") + '</td><td data-label="主要权益">' + benefit + '</td></tr>';
  }).join("");
  const table = (title, kind) => '<h3>' + title + '</h3><div style="overflow-x:auto" tabindex="0" role="region" aria-label="' + title + '"><table class="data-table pricing-table"><thead><tr><th>套餐</th><th>价格（人民币）</th><th>有效期</th><th>主要权益</th></tr></thead><tbody>' + rows(kind) + '</tbody></table></div>';
  const html = '<section class="article-section" id="current-plans" data-catalog-fingerprint="' + pricingFingerprint(pricing) + '"><h2>面试稳如何收费？</h2><p>面试稳提供按天会员与积分包。以下已上架套餐来自生产商品目录，无需登录即可查看；购买仍通过账户内的积分与会员页面完成。</p>'
    + table("按天会员", "time_pass") + table("积分包", "points_pack")
    + '<p>目录版本 ' + rates.catalogVersion + ' · 价格同步时间：<time datetime="' + now.toISOString() + '">' + now.toISOString() + '</time>。价格可能调整，付款前请核对订单金额与权益。</p>'
    + '<h3>积分按什么规则消耗？</h3><ul><li>普通回答：' + rates.answerPoints + ' 积分/次；截图回答：' + rates.screenshotAnswerPoints + ' 积分/次。</li><li>实时面试：' + rates.realtimeMinutePoints + ' 积分/分钟；有效会员的实时面试、回答与截图不扣积分。暂停收音不产生新的分钟费用。</li><li>笔试模式入场：' + rates.writtenExamPoints + ' 积分/次，会员也需扣除入场积分。</li><li>知识材料索引：最低 ' + rates.knowledgeIndexMinimumPoints + ' 积分，每 5,000 Token ' + rates.knowledgeIndexPointsPer1000Tokens * 5 + ' 积分，不足一档按一档计算；可用会员索引额度优先抵扣，处理前须确认报价。</li></ul>'
    + '<p><a class="button primary" href="/app/billing">前往积分与会员</a> <a href="/login">登录或免费体验</a></p></section>';
  return template.replace(marker, html);
}

export function assertCurrentPricing(html, pricing, now = new Date()) {
  if (!html.includes('data-catalog-fingerprint="' + pricingFingerprint(pricing) + '"')) throw new Error("Production catalogue changed: rebuild Web before publishing");
  const stamp = html.match(/<time datetime="([^"]+)"/)?.[1];
  const age = now.getTime() - Date.parse(stamp ?? "");
  if (!Number.isFinite(age) || age < -60000 || age > 86400000) throw new Error("Pricing snapshot expired: rebuild Web before publishing");
  if (!html.includes(renderPricing("<!-- PRODUCTION_PRICING -->", pricing, new Date(stamp)))) throw new Error("Rendered prices or benefits do not match production catalogue");
}
