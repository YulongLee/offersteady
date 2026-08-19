## Context

OfferSteady is a Vite React SPA behind an explicit Nginx route allowlist. The homepage and `/guide` now provide correct server-delivered metadata, canonical URLs, public caching, and deterministic release checks. The remaining growth gap is not an indexing blocker: the public topic footprint is small, AI systems lack an explicit canonical fact source, and homepage mobile LCP varies across laboratory runs.

The implementation must not add API calls, user tracking, runtime dependencies, or state shared with authenticated product routes. Public content must describe only existing capabilities and must preserve the product boundary that AI output is a suggestion rather than a guaranteed or deceptive answer.

## Goals / Non-Goals

**Goals:**

- Add six curated Chinese topic pages for existing product capabilities and common setup intent.
- Make every public topic page useful without JavaScript and connect it through crawlable navigation.
- Give search engines and answer engines canonical, consistent product facts through JSON-LD, `llms.txt`, `llms-full.txt`, and a compact JSON fact file.
- Reduce avoidable public-page image and payload cost and enforce performance budgets in regression checks.
- Preserve all existing product routes, APIs, business state, and user interactions.

**Non-Goals:**

- No changes to authentication, interviews, realtime audio processing, screenshots, materials, knowledge retrieval, billing, payments, membership, admin, or desktop companion behavior.
- No ranking, traffic, conversion, review, customer, accuracy, legal entity, or performance claims without evidence.
- No mass-generated blog, doorway pages, FAQ rich-result schema, HowTo schema, backlink outreach, analytics mutation, or sitemap submission.
- No Search Console, GA4, or keyword-volume claims until first-party/provider credentials are available.

## Decisions

### Publish small static topic pages outside the authenticated SPA

Six allowlisted pages will cover the current high-intent cluster: AI interview assistant, realtime interview support, screenshot question assistance, interview review, audio troubleshooting, and interview preparation. Each page is static HTML with a shared lightweight stylesheet, one H1, concise sections, route-specific metadata, self-canonical, WebPage/BreadcrumbList JSON-LD, and ordinary links.

This is preferred over adding a CMS or SSR framework because it adds no runtime dependency or backend risk. It is preferred over client-only React routes because crawlers and users receive complete content before JavaScript.

### Use a shared truthful content contract

Public pages will use only facts already represented in the product and guide. They will describe setup, boundaries, and user-controlled workflows, and will avoid claims about guaranteed offers, covert use, official platform integrations, accuracy percentages, or named customers. Topic pages will link to the guide and login rather than inventing new product behavior.

### Publish explicit GEO discovery artifacts

`llms.txt` will provide a concise product description and canonical page list. `llms-full.txt` will provide a longer factual summary and product boundaries. `public-facts.json` will expose versioned facts, canonical URLs, supported public capabilities, privacy boundaries, and contact routes. These artifacts are advisory discovery sources and do not replace HTML or JSON-LD.

This is preferred over adding speculative AI-specific schema types because standard WebPage, Organization, WebSite, SoftwareApplication, and BreadcrumbList data remain the most portable structured signals.

### Keep a single explicit public-route registry in verification

The sitemap, Nginx route mappings, page files, canonical URLs, metadata, structured data, internal links, and GEO artifacts will be validated together. A missing page, mismatched canonical, noindex header, invalid JSON-LD, or undiscoverable sitemap URL will fail verification.

### Optimize existing public assets without redesigning the landing page

The homepage will retain its current layout and interactions. Optimization will focus on explicit image dimensions, lazy loading below the fold, decoding hints, lighter formats where assets permit, public static caching, and a measured bundle/image budget. The authenticated SPA bundle remains unchanged unless a safe shared asset optimization is proven by tests.

## Risks / Trade-offs

- [Static page copy can drift from product behavior] → Keep claims narrow, link to the canonical guide, and validate required facts and links in one regression script.
- [Additional sitemap URLs can dilute quality] → Limit the first release to six distinct intents with substantial unique content; do not generate permutations.
- [GEO files are not a ranking guarantee] → Treat them as citation-readiness aids and keep traditional HTML, internal links, and schema as the primary signals.
- [Performance scores vary by network] → Use three-run laboratory medians for reporting and deterministic byte/dimension checks for releases; do not claim field CWV without CrUX.
- [Static pages may look inconsistent] → Use one shared stylesheet and the existing public brand tokens without importing the SPA bundle.

## Migration Plan

1. Generate the durable SEO workspace and page/keyword map from current evidence.
2. Add public pages and GEO artifacts, then update Nginx, sitemap, homepage/guide navigation, and verification scripts together.
3. Run focused SEO/GEO checks, schema validation, Web tests, typecheck, build, route smoke tests, and Lighthouse comparisons.
4. Deploy the Web image only; do not restart backend, database, Redis, admin, or desktop services.
5. Roll back the Web image and commit together if any existing route or public health check regresses.

## Open Questions

- The registered legal operator name remains unconfirmed and will not be added as `legalName` in this change.
- The homepage marketing metrics remain unverified and will not be strengthened or reused as structured data.
- Search Console, GA4, Baidu, CrUX, and paid keyword data remain unavailable; monitoring artifacts will label those metrics unknown.
