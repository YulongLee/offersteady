import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { generateHomepageDownloads } from "./generate-homepage-downloads.mjs";
import { renderCommercialHomepage } from "./render-commercial-homepage.mjs";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
await generateHomepageDownloads(root);
const catalogue = JSON.parse(await readFile(resolve(root, "src/public-review-pages.json"), "utf8"));
const publicDir = resolve(root, "public");
const shareImage = `${catalogue.siteUrl}/assets/brand/share-card.png`;
const lastmod = catalogue.updatedDateIso;
const escapeHtml = (value) => String(value)
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;");
const escapeJsonForHtml = (value) => JSON.stringify(value).replaceAll("<", "\\u003c");
const publicNavigation = [
  ["Features", "/features"],
  ["Interview topics", "/interview-questions"],
  ["Guides", "/guides"],
  ["Pricing", "/pricing"],
  ["Download", "/download"],
];
const companyNavigation = [
  ["About", "/about"],
  ["Contact", "/contact"],
  ["Security", "/security"],
  ["Terms of Service", "/terms"],
  ["Privacy Policy", "/privacy"],
  ["Refund Policy", "/refund-policy"],
];
const linkList = (links) => links.map(([label, href]) => `<a href="${href}">${escapeHtml(label)}</a>`).join(" · ");
const prohibitedCopy = ["cheating", "undetectable", "anti-detection", "bypass monitoring"];

const homepagePath = resolve(root, "index.html");
let homepage = await readFile(homepagePath, "utf8");
const home = JSON.parse(await readFile(resolve(root, "src/homepage-commercial.json"), "utf8"));
homepage = homepage.replace(/(<meta\s+name="description"\s+content=")[^"]*(")/, (_, prefix, suffix) => prefix + escapeHtml(home.metaDescription) + suffix);
homepage = homepage.replace(/(<meta (?:property="og:description"|name="twitter:description") content=")[^"]*(")/g, (_, prefix, suffix) => prefix + escapeHtml(home.metaDescription) + suffix);
const downloadsHtml = homepage.match(/<!-- homepage-downloads:start -->[\s\S]*?<!-- homepage-downloads:end -->/)?.[0];
if (!downloadsHtml) throw new Error("Homepage download marker is missing");
homepage = homepage.replace(/<main class="seo-prerender">[\s\S]*?<\/main>/, () => renderCommercialHomepage({ catalogue, home, downloadsHtml }));
const pricingPage = catalogue.pages.find(page => page.slug === "pricing");
homepage = homepage.replace(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/, (_, source) => {
  const schema = JSON.parse(source);
  for (const item of schema["@graph"]) {
    if (["SoftwareApplication", "WebSite"].includes(item["@type"])) item.description = catalogue.productDescription;
    if (item["@type"] === "SoftwareApplication") item.offers = pricingPage.plans.map(plan => ({
      "@type": "Offer", name: plan.name, price: plan.price.replace("$", ""), priceCurrency: "USD",
      url: `${catalogue.siteUrl}/pricing`,
      description: `${plan.billing}. ${plan.accessStarts} ${plan.href ? "Available through Start Free." : catalogue.checkoutNotice}`,
    }));
  }
  return `<script type="application/ld+json">${JSON.stringify(schema, null, 2).replaceAll("<", "\\u003c")}</script>`;
});
await writeFile(homepagePath, homepage);

function breadcrumbSchema(page, canonical) {
  const segments = page.slug.split("/");
  const items = [{ "@type": "ListItem", position: 1, name: "Home", item: `${catalogue.siteUrl}/` }];
  if (segments.length > 1) {
    const parent = catalogue.pages.find((candidate) => candidate.slug === segments[0]);
    items.push({ "@type": "ListItem", position: 2, name: parent?.h1 ?? segments[0], item: `${catalogue.siteUrl}/${segments[0]}` });
  }
  items.push({ "@type": "ListItem", position: items.length + 1, name: page.h1, item: canonical });
  return { "@type": "BreadcrumbList", "@id": `${canonical}#breadcrumb`, itemListElement: items };
}

function pageSchema(page, canonical) {
  const graph = [
    {
      "@type": "WebPage",
      "@id": `${canonical}#webpage`,
      url: canonical,
      name: page.title,
      description: page.description,
      inLanguage: "en",
      isPartOf: { "@id": `${catalogue.siteUrl}/#website` },
      about: { "@id": `${catalogue.siteUrl}/#organization` },
      breadcrumb: { "@id": `${canonical}#breadcrumb` },
      dateModified: lastmod,
    },
    breadcrumbSchema(page, canonical),
  ];
  if (page.slug === "pricing") {
    graph.push({
      "@type": "SoftwareApplication",
      "@id": `${catalogue.siteUrl}/#software`,
      name: "OfferSteady",
      url: catalogue.siteUrl,
      applicationCategory: "BusinessApplication",
      operatingSystem: "Web, macOS, Windows",
      description: "AI interview guidance for preparation, live sessions, screenshot questions, written assessments, and review.",
      offers: page.plans.map((plan) => ({
        "@type": "Offer",
        name: plan.name,
        price: plan.price.replace("$", ""),
        priceCurrency: "USD",
        url: canonical,
        description: `${plan.description} ${plan.billing}. ${plan.accessStarts} ${plan.href ? "Available through Start Free." : catalogue.checkoutNotice}`,
      })),
    });
  }
  return { "@context": "https://schema.org", "@graph": graph };
}

for (const page of catalogue.pages) {
  const canonical = `${catalogue.siteUrl}/${page.slug}`;
  const plans = (page.plans ?? []).map((plan) => `<article><h2>${escapeHtml(plan.name)}</h2><p><strong>${escapeHtml(`${plan.price}${plan.term}`)}</strong></p><p>${escapeHtml(plan.description)}</p><ul>${plan.features.map((feature) => `<li>${escapeHtml(feature)}</li>`).join("")}</ul><p>${escapeHtml(plan.billing)}</p><p>Access begins: ${escapeHtml(plan.accessStarts)}</p>${plan.href ? `<p><a href="${escapeHtml(plan.href)}">${escapeHtml(plan.action)}</a></p>` : `<p><button type="button" disabled>${escapeHtml(plan.action)}</button></p>`}</article>`).join("");
  const actions = (page.actions ?? []).map((action) => `<div><p><a href="${escapeHtml(action.href)}">${escapeHtml(action.label)}</a></p><p>${escapeHtml(action.detail)}</p></div>`).join("");
  const sections = page.sections.map((section) => `<section><h2>${escapeHtml(section.heading)}</h2>${section.paragraphs.map((paragraph) => `<p>${escapeHtml(paragraph)}</p>`).join("")}</section>`).join("");
  const html = `<!doctype html>
<html lang="en"><head><meta charset="UTF-8" /><meta name="viewport" content="width=device-width, initial-scale=1.0" /><meta name="theme-color" content="#0b1020" /><link rel="icon" href="/assets/brand/favicon.png" type="image/png" /><title>${escapeHtml(page.title)}</title><meta name="description" content="${escapeHtml(page.description)}" /><link rel="canonical" href="${canonical}" /><meta property="og:type" content="website" /><meta property="og:site_name" content="OfferSteady" /><meta property="og:locale" content="en_US" /><meta property="og:title" content="${escapeHtml(page.title)}" /><meta property="og:description" content="${escapeHtml(page.description)}" /><meta property="og:url" content="${canonical}" /><meta property="og:image" content="${shareImage}" /><meta property="og:image:width" content="1200" /><meta property="og:image:height" content="630" /><meta property="og:image:alt" content="OfferSteady AI interview assistant" /><meta name="twitter:card" content="summary_large_image" /><meta name="twitter:title" content="${escapeHtml(page.title)}" /><meta name="twitter:description" content="${escapeHtml(page.description)}" /><meta name="twitter:image" content="${shareImage}" /><script type="application/ld+json">${escapeJsonForHtml(pageSchema(page, canonical))}</script><style>body{margin:0;background:#090e16}.seo-prerender{width:min(1080px,calc(100% - 40px));margin:0 auto;padding:64px 0;color:#eef4f8;font-family:system-ui,sans-serif}.seo-prerender h1{max-width:860px;font-size:clamp(38px,6vw,64px);line-height:1.08}.seo-prerender h2{margin-top:36px}.seo-prerender p,.seo-prerender li{max-width:860px;color:#aeb9c8;line-height:1.75}.seo-prerender a{color:#6ee7bd}.seo-prerender nav,.seo-prerender footer{margin-top:32px}.seo-plan-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px}.seo-plan-grid article{padding:22px;border:1px solid #334155;border-radius:18px}.seo-actions{margin:28px 0}.seo-actions a{display:inline-block;padding:12px 18px;border-radius:12px;background:#6ee7bd;color:#07111a;font-weight:700}@media(max-width:720px){.seo-plan-grid{grid-template-columns:1fr}}</style></head><body><div id="root"><main class="seo-prerender"><header><p>${escapeHtml(page.eyebrow)}</p><h1>${escapeHtml(page.h1)}</h1><p>${escapeHtml(page.intro)}</p>${["terms", "privacy", "refund-policy"].includes(page.slug) ? `<p>Effective date / last updated: ${escapeHtml(catalogue.updatedAt)}</p>` : ""}${actions ? `<div class="seo-actions">${actions}</div>` : ""}<nav aria-label="Public navigation"><a href="/">Home</a> · ${linkList(publicNavigation)}</nav></header>${plans ? `<section class="seo-plan-grid">${plans}</section>` : ""}${sections}<footer><p>AI output is guidance. Verify every claim, answer from your real experience, and follow the interview organiser's rules.</p><p>${linkList(publicNavigation)}</p><p>${linkList(companyNavigation)}</p><p>Support: <a href="mailto:${catalogue.supportEmail}">${catalogue.supportEmail}</a></p><p>Operated by ${escapeHtml(catalogue.operator)} · ${escapeHtml(catalogue.operatorLocation)}</p><p>Last updated: ${escapeHtml(catalogue.updatedAt)}</p><p>© 2026 OfferSteady</p></footer></main></div><script type="module" src="/src/main.tsx"></script></body></html>`;
  const destination = resolve(root, page.slug, "index.html");
  await mkdir(dirname(destination), { recursive: true });
  await writeFile(destination, html);
}

const sitemapUrls = [
  { url: `${catalogue.siteUrl}/`, modified: lastmod },
  ...catalogue.pages.map((page) => ({ url: `${catalogue.siteUrl}/${page.slug}`, modified: lastmod })),
];
const sitemap = `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${sitemapUrls.map(({ url, modified }) => `  <url><loc>${escapeHtml(url)}</loc><lastmod>${modified}</lastmod></url>`).join("\n")}\n</urlset>\n`;
await writeFile(resolve(publicDir, "sitemap.xml"), sitemap);

const llms = `# OfferSteady\n> OfferSteady is an English AI interview assistant for preparation, live transcription, grounded answer guidance, user-triggered screenshot questions, written assessments, and interview review.\n\n## Product\n${publicNavigation.map(([label, href]) => `- [${label}](${catalogue.siteUrl}${href})`).join("\n")}\n\n## Company and policies\n${companyNavigation.map(([label, href]) => `- [${label}](${catalogue.siteUrl}${href})`).join("\n")}\n\n## Responsible use\n- AI output is guidance, not a hiring guarantee.\n- Users must verify every claim and answer from their real experience.\n- Users must follow the interview organiser's rules for recording, confidentiality, screen capture, and AI assistance.\n\nSupport: ${catalogue.supportEmail}\n`;
await writeFile(resolve(publicDir, "llms.txt"), llms);

const llmsFull = `# OfferSteady: public product information\n\nOfferSteady is operated by ${catalogue.operator}, ${catalogue.operatorLocation}. The Global product is an English Web workspace and desktop Companion for interview preparation, live transcription, grounded answer guidance, typed questions, user-triggered screenshots, written assessments, and review.\n\n## How it works\n\nUsers select a resume, job description, and optional knowledge materials for a session. The connected desktop Companion provides enabled microphone, supported computer-output audio, and user-triggered screenshot inputs. The Web workspace displays progressive transcripts and can prepare guidance manually or through optional Auto Answer for confirmed interviewer questions. Raw audio is not stored by default.\n\n## Plans\n\n${catalogue.pages.find(page => page.slug === "pricing").plans.map(plan => `${plan.name}: ${plan.price}${plan.term}. ${plan.billing}. ${plan.accessStarts} Includes: ${plan.features.join("; ")}.`).join("\n")} ${catalogue.checkoutNotice}\n\n## Boundaries\n\nAI output is guidance and can be inaccurate. Users must verify every claim, keep answers faithful to their real experience, obtain consent where required, and follow the interview organiser's rules for AI assistance, recording, screen capture, confidentiality, and external tools. Opening the website alone does not start audio or screenshot capture.\n\n## Canonical sources\n- [Home](${catalogue.siteUrl}/)\n${catalogue.pages.map((page) => `- [${page.h1}](${catalogue.siteUrl}/${page.slug})`).join("\n")}\n\nLast reviewed: ${catalogue.updatedAt}\nSupport: ${catalogue.supportEmail}\n`;
await writeFile(resolve(publicDir, "llms-full.txt"), llmsFull);

const publicFacts = {
  version: 1,
  lastReviewed: lastmod,
  canonicalSite: catalogue.siteUrl,
  name: "OfferSteady",
  description: "English AI interview guidance for preparation, live sessions, screenshot questions, written assessments, and review.",
  operator: { legalName: catalogue.operator, location: catalogue.operatorLocation },
  support: { email: catalogue.supportEmail, url: `${catalogue.siteUrl}/contact` },
  product: {
    languages: ["English"],
    platforms: ["Web", "macOS", "Windows"],
    capabilities: ["live transcription", "grounded answer guidance", "typed questions", "user-triggered screenshot questions", "written assessments", "interview review"],
    rawAudioStoredByDefault: false,
    guidanceOnly: true,
  },
  pricing: {
    currency: "USD",
    checkoutActive: false,
    paymentNotice: catalogue.checkoutNotice,
    plans: catalogue.pages.find(page => page.slug === "pricing").plans.map(plan => ({
      name: plan.name, price: Number(plan.price.replace("$", "")), term: plan.term.trim() || null,
      status: plan.href ? "available" : "approval-required",
      billing: plan.billing, accessStarts: plan.accessStarts, features: plan.features,
    })),
  },
  canonicalPages: sitemapUrls.map(({ url }) => url),
  responsibleUse: ["Verify every claim.", "Answer from real experience.", "Follow the interview organiser's rules."],
};
await writeFile(resolve(publicDir, "public-facts.json"), `${JSON.stringify(publicFacts, null, 2)}\n`);

const notFound = `<!doctype html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>Page Not Found | OfferSteady</title><style>body{margin:0;background:#090e16;color:#eef4f8;font-family:system-ui,sans-serif}main{width:min(720px,calc(100% - 40px));margin:15vh auto}p{color:#aeb9c8;line-height:1.7}a{color:#6ee7bd}</style></head><body><main><p>404</p><h1>Page not found</h1><p>The address may be incorrect or the page may have moved.</p><p><a href="/">Return to OfferSteady</a></p></main></body></html>`;
await writeFile(resolve(publicDir, "404.html"), notFound);

const searchableText = JSON.stringify({ catalogue, llms, llmsFull, publicFacts }).toLowerCase();
for (const phrase of prohibitedCopy) {
  if (searchableText.includes(phrase)) throw new Error(`prohibited public copy: ${phrase}`);
}

console.log(`generated ${catalogue.pages.length} public HTML entries and ${sitemapUrls.length} sitemap URLs`);
