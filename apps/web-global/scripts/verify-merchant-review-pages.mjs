import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(fileURLToPath(new URL("..", import.meta.url)));
const repositoryRoot = resolve(root, "../..");
const catalogue = JSON.parse(await readFile(resolve(root, "src/public-review-pages.json"), "utf8"));
const failures = [];
const publicUrls = [`${catalogue.siteUrl}/`, ...catalogue.pages.map((page) => `${catalogue.siteUrl}/${page.slug}`)];
const seen = { titles: new Set(), descriptions: new Set(), canonicals: new Set(), h1s: new Set() };
const extractJsonLd = (html) => [...html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)].map((match) => JSON.parse(match[1]));
const growthContentRoutes = new Set(["features", "features/ai-interview-assistant", "features/realtime-interview", "features/screenshot-answer", "features/interview-review", "guides", "interview-questions", "download"]);
const wordCount = (value) => String(value).trim().split(/\s+/).filter(Boolean).length;

for (const page of catalogue.pages) {
  const html = await readFile(resolve(root, "dist", page.slug, "index.html"), "utf8");
  const expectedCanonical = `${catalogue.siteUrl}/${page.slug}`;
  const expectations = [
    ["title", `<title>${page.title}</title>`, page.title, seen.titles],
    ["description", `name="description" content="${page.description}"`, page.description, seen.descriptions],
    ["canonical", `rel="canonical" href="${expectedCanonical}"`, expectedCanonical, seen.canonicals],
    ["h1", `<h1>${page.h1}</h1>`, page.h1, seen.h1s],
  ];
  for (const [label, expected, uniqueValue, values] of expectations) {
    if (!html.includes(expected)) failures.push(`${page.slug}: missing ${label}`);
    if (values.has(uniqueValue)) failures.push(`${page.slug}: duplicate ${label}`);
    values.add(uniqueValue);
  }
  for (const expected of [catalogue.operator, catalogue.operatorLocation, catalogue.supportEmail, "Operated by", 'href="/refund-policy"', 'href="/terms"', 'href="/privacy"']) {
    if (!html.includes(expected)) failures.push(`${page.slug}: missing public disclosure ${expected}`);
  }
  if (["terms", "privacy", "refund-policy"].includes(page.slug) && !html.includes("Effective date")) failures.push(`${page.slug}: missing effective date`);
  if (page.title.length < 30 || page.title.length > 60) failures.push(`${page.slug}: title length ${page.title.length} outside 30-60`);
  if (page.description.length < 120 || page.description.length > 160) failures.push(`${page.slug}: description length ${page.description.length} outside 120-160`);
  if (growthContentRoutes.has(page.slug)) {
    const searchableCopy = [page.h1, page.intro, ...page.sections.flatMap((section) => [section.heading, ...section.paragraphs])].join(" ");
    if (wordCount(searchableCopy) < 450) failures.push(`${page.slug}: growth content below 450 words`);
  }
  for (const action of page.actions ?? []) {
    if (!action.href.startsWith("/") || !html.includes(`<a href="${action.href}">${action.label}</a>`)) failures.push(`${page.slug}: missing or unsafe public action ${action.label}`);
  }
  if (!html.includes(page.sections[0].paragraphs[0])) failures.push(`${page.slug}: missing route-specific body`);
  if (html.includes("<h1>Stay focused. Answer with confidence.</h1>")) failures.push(`${page.slug}: received home-page H1`);
  for (const expected of [
    `property="og:url" content="${expectedCanonical}"`,
    `property="og:image" content="${catalogue.siteUrl}/assets/brand/share-card.png"`,
    `name="twitter:card" content="summary_large_image"`,
    `name="twitter:image" content="${catalogue.siteUrl}/assets/brand/share-card.png"`,
  ]) if (!html.includes(expected)) failures.push(`${page.slug}: missing social metadata ${expected}`);
  try {
    const schemas = extractJsonLd(html);
    const types = schemas.flatMap((schema) => schema["@graph"] ?? [schema]).map((entry) => entry["@type"]);
    if (!types.includes("WebPage") || !types.includes("BreadcrumbList")) failures.push(`${page.slug}: missing WebPage/BreadcrumbList schema`);
    if (page.slug === "pricing" && !types.includes("SoftwareApplication")) failures.push("pricing: missing SoftwareApplication offers");
  } catch (error) {
    failures.push(`${page.slug}: invalid JSON-LD (${error.message})`);
  }
}

const pricing = await readFile(resolve(root, "dist/pricing/index.html"), "utf8");
for (const expected of ["Free", "$0", "Interview Day Pass", "$9.99 / 24 hours", "Pro Weekly", "$49.99 / 7 days", "Pro Monthly", "$99.99/month", "Job Hunt", "$199.99 / 90 days", "Start Free", "Checkout requires provider approval"]) {
  if (!pricing.includes(expected)) failures.push(`pricing: missing ${expected}`);
}
if ((pricing.match(/<button type="button" disabled>/g) ?? []).length !== 4) failures.push("pricing: expected four disabled purchase controls");
for (const plan of catalogue.pages.find(page => page.slug === "pricing").plans) {
  if (!pricing.includes(plan.billing) || !pricing.includes(plan.accessStarts)) failures.push(`pricing: missing billing/access for ${plan.name}`);
}
if (/\/api\/v1\/global-commerce|checkoutUrl|Choose plan|Buy now/i.test(pricing)) failures.push("pricing: contains an active-payment control");

const download = await readFile(resolve(root, "dist/download/index.html"), "utf8");
for (const expected of ['href="/login">Start Free</a>', "Verified Companion release options appear in the interview preparation flow."]) {
  if (!download.includes(expected)) failures.push(`download: missing conversion action ${expected}`);
}
if (/href="[^"]+\.(?:dmg|pkg|exe|msi|zip)"/i.test(download)) failures.push("download: exposes an unapproved installer URL");

const home = await readFile(resolve(root, "dist/index.html"), "utf8");
const commercial = JSON.parse(await readFile(resolve(root, "src/homepage-commercial.json"), "utf8"));
const escaped = value => value.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
for (const value of [catalogue.productDescription, catalogue.guidanceNotice, commercial.metaDescription, commercial.accessNote, commercial.checkoutNote, commercial.closingTitle, ...commercial.benefits.flatMap(item => [item.title, item.body]), ...commercial.faqs.flatMap(item => [item.question, item.answer])]) {
  if (!home.includes(escaped(value))) failures.push(`home: missing shared commercial copy ${value}`);
}
for (const video of commercial.videos) if (!home.includes(video.src) || !home.includes(video.poster)) failures.push(`home: missing video ${video.label}`);
if ((home.match(/controls muted playsinline preload="metadata"/g) ?? []).length !== 2) failures.push("home: video control attributes changed");
if (home.indexOf('id="plans"') > home.indexOf('id="product-tour"')) failures.push("home: pricing must precede tour");
for (const expected of [
  catalogue.heroTitle,
  "$9.99 / 24 hours",
  "$49.99 / 7 days",
  "$99.99/month",
  "$199.99 / 90 days",
  'property="og:url" content="https://offersteady.com/"',
  'property="og:image" content="https://offersteady.com/assets/brand/share-card.png"',
  'name="twitter:card" content="summary_large_image"',
]) if (!home.includes(expected)) failures.push(`home: missing ${expected}`);
for (const type of ["Organization", "WebSite", "SoftwareApplication"]) {
  if (!home.includes(`"@type": "${type}"`)) failures.push(`home: missing ${type} schema`);
}
if (/href="\/guide"|>User guide<|>Read the guide</i.test(home)) failures.push("home: international user-manual link remains");

const sitemap = await readFile(resolve(root, "dist/sitemap.xml"), "utf8");
const sitemapUrls = [...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)].map((match) => match[1]);
if (JSON.stringify(sitemapUrls) !== JSON.stringify(publicUrls)) failures.push("sitemap: URL set or order differs from public catalogue");
if (sitemap.split(`<lastmod>${catalogue.updatedDateIso}</lastmod>`).length - 1 !== publicUrls.length) failures.push("sitemap: lastmod coverage mismatch");

const robots = await readFile(resolve(root, "dist/robots.txt"), "utf8");
if (!robots.includes(`Sitemap: ${catalogue.siteUrl}/sitemap.xml`)) failures.push("robots: sitemap reference mismatch");

const llms = await readFile(resolve(root, "dist/llms.txt"), "utf8");
const llmsFull = await readFile(resolve(root, "dist/llms-full.txt"), "utf8");
if (!llms.startsWith("# OfferSteady\n> ")) failures.push("llms.txt: missing title/description");
if (llms.includes("<!doctype html>") || llmsFull.includes("<!doctype html>")) failures.push("GEO text: homepage fallback detected");
for (const expected of ["## Product", "## Company and policies", "## Responsible use", catalogue.supportEmail]) {
  if (!llms.includes(expected)) failures.push(`llms.txt: missing ${expected}`);
}
for (const url of publicUrls) if (!llmsFull.includes(url)) failures.push(`llms-full.txt: missing ${url}`);

const publicFactsText = await readFile(resolve(root, "dist/public-facts.json"), "utf8");
try {
  const facts = JSON.parse(publicFactsText);
  if (facts.canonicalSite !== catalogue.siteUrl) failures.push("public-facts: canonical mismatch");
  if (facts.pricing?.checkoutActive !== false) failures.push("public-facts: checkout must remain disabled");
  if (JSON.stringify(facts.canonicalPages) !== JSON.stringify(publicUrls)) failures.push("public-facts: canonical page mismatch");
} catch (error) {
  failures.push(`public-facts: invalid JSON (${error.message})`);
}

const notFound = await readFile(resolve(root, "dist/404.html"), "utf8");
if (!notFound.includes('name="robots" content="noindex,nofollow"') || !notFound.includes("<h1>Page not found</h1>")) failures.push("404: missing noindex document");

const shareImage = await readFile(resolve(root, "dist/assets/brand/share-card.png"));
if (shareImage.readUInt32BE(16) !== 1200 || shareImage.readUInt32BE(20) !== 630) failures.push("share image: dimensions must be 1200x630");
if (shareImage.byteLength > 300_000) failures.push(`share image: ${shareImage.byteLength} bytes exceeds 300000-byte limit`);
const manifest = JSON.parse(await readFile(resolve(root, "dist/assets/assets.manifest.json"), "utf8"));
const manifestEntry = manifest.entries.find((entry) => entry.id === "brand.share-card");
const shareHash = createHash("sha256").update(shareImage).digest("hex");
if (!manifestEntry || manifestEntry.sha256 !== shareHash) failures.push("share image: manifest hash mismatch");

const nginx = await readFile(resolve(repositoryRoot, "infra/nginx/global-web.conf"), "utf8");
for (const expected of ["/llms.txt", "/llms-full.txt", "/public-facts.json", "X-Robots-Tag", "noindex, nofollow", "return 404;"] ) {
  if (!nginx.includes(expected)) failures.push(`nginx: missing ${expected}`);
}
if (!nginx.includes("return 301 https://offersteady.com/$public_page$is_args$args;")) failures.push("nginx: trailing-slash redirect does not preserve query parameters");

const allPublicText = [home, pricing, ...catalogue.pages.map((page) => JSON.stringify(page)), llms, llmsFull, publicFactsText].join("\n").toLowerCase();
for (const prohibited of ["coming soon", "checkout is not active", "paid checkout", "cheating", "undetectable", "anti-detection", "guaranteed offer", "secretly", "bypass monitoring"]) {
  if (allPublicText.includes(prohibited)) failures.push(`copy: prohibited phrase ${prohibited}`);
}

if (failures.length) {
  console.error(failures.join("\n"));
  process.exit(1);
}
console.log(`global-public-search:ok (${publicUrls.length} indexable URLs)`);
