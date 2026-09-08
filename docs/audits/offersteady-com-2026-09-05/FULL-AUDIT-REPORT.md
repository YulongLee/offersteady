# OfferSteady International SEO/GEO Audit

Date: 2026-09-05  
Scope: production site `https://offersteady.com`, direct HTTP responses without client-side JavaScript, public discovery files, representative public routes, and external search visibility.  
Production follow-up: P0 public-search delivery fixes were deployed as `global-seo-geo-20260905.1` after the baseline audit.

## Post-deployment verification

The production follow-up closed the confirmed P0 crawling defects without changing the Global Backend or domestic product:

- Sixteen approved indexable URLs now return HTTP 200 with route-specific title, meta description, canonical, H1, substantive body, and JSON-LD in the initial HTML.
- Pricing initial HTML contains the exact visible values `$19.99/week` and `$39.99/month`, with paid checkout still labelled `Coming Soon` and disabled.
- `/llms.txt`, `/llms-full.txt`, and `/public-facts.json` return their real text/JSON bodies with the expected MIME types.
- `sitemap.xml` contains exactly 16 canonical URLs and 16 maintained `lastmod` values dated `2026-09-05`.
- `/login` and `/app` return `X-Robots-Tag: noindex, nofollow`; an arbitrary unknown path and the removed public `/guide` route return HTTP 404.
- HTTP and HTTPS `www` requests permanently redirect to the apex host while preserving path and query.
- Public HTML responses expose HSTS, CSP, nosniff, frame, referrer, and permissions-policy headers.
- The Global Backend remained healthy on release `global-remove-user-manual-20260904.1`; Backend, PostgreSQL, Redis, Admin, and Analytics were not restarted.

Regional field performance, index coverage, rankings, and external citations remain unverified until Search Console, Bing Webmaster Tools, analytics, and target-market field data are connected.

## Audit summary

Directional SEO health score: **38/100 — Poor, with moderate confidence**.

The production site has a sound merchant-review foundation: HTTPS works, the homepage and seven commercial/legal pages return route-specific HTML, their canonical URLs are correct, contact details are consistent, and the tested internal links are healthy. The main search-growth surface is not yet operational. Feature, guide, topic, download, login, and unknown routes return the homepage HTML with the homepage canonical. GEO discovery endpoints also return homepage HTML instead of their declared formats.

Positive evidence used for the directional score:

1. HTTPS responds successfully.
2. `/pricing`, `/terms`, `/privacy`, `/refund-policy`, `/contact`, `/about`, and `/security` return unique title, description, canonical, H1, and body content.
3. `robots.txt` allows public crawling and points to a sitemap.
4. The 18-page internal crawl found no broken links or orphan candidates.
5. Terms, About, and Contact expose the operator; the support email is consistent.

Deficit evidence used for the directional score:

1. Search-intent routes return the homepage document and canonical.
2. Unknown URLs return HTTP 200 instead of 404.
3. `llms.txt`, `llms-full.txt`, and `public-facts.json` return HTML homepage content.
4. No JSON-LD was detected on any sampled HTML document.
5. Homepage content is thin and has weak citation/experience signals.
6. External exact-domain and brand searches did not surface OfferSteady in sampled results.
7. Public response latency was high from the audit location and field CWV data is unavailable.

The score is directional rather than an absolute ranking forecast. Search Console, Bing Webmaster Tools, GA4, and CrUX field data were not available.

## Findings

| Area | Severity | Confidence | Finding | Evidence | Impact | Fix |
|---|---|---|---|---|---|---|
| Public rendering | Critical | Confirmed | Search-intent routes do not return their own server-readable pages. | `/features`, four `/features/*` pages, `/guides`, `/interview-questions`, `/guide`, and `/download` all returned 5,725-byte homepage HTML, title `OfferSteady \| AI Interview Assistant`, H1 `Stay focused in every interview.`, and canonical `/`. | Search engines and AI crawlers cannot reliably index or cite these routes as distinct content. | Produce unique static/SSR HTML for every indexable route and add exact Nginx route mappings before the SPA fallback. |
| HTTP status | Critical | Confirmed | Unknown paths are soft 404s. | `/definitely-not-a-real-page-20260905` returned HTTP 200 and homepage HTML. | Wastes crawl budget, creates duplicate URLs, and weakens index quality. | Return a real 404 status and a useful 404 document for unknown public paths. |
| GEO discovery | Critical | Confirmed | AI discovery resources are broken in production. | `/llms.txt`, `/llms-full.txt`, and `/public-facts.json` returned `text/html`, HTTP 200, and the homepage body. | AI systems receive no reliable machine-readable product facts or canonical source map. | Serve actual plain-text `llms` files and JSON facts with correct content types and explicit exact-location rules. |
| Index control | Warning | Confirmed | Application/login paths lack server-side index control. | `/login` and `/app` return homepage HTML with no robots meta or `X-Robots-Tag`. | Private/product shell URLs can enter crawl/render queues and compete with the homepage. | Serve the correct shell with `noindex, nofollow` in initial HTML or response headers; keep them out of sitemap. |
| Sitemap | Warning | Confirmed | Sitemap covers only eight merchant-review pages and has no `lastmod`. | Production `sitemap.xml` lists `/`, Pricing, five policy/company pages, and Security only. | Search-intent pages are not declared for discovery; freshness cannot be communicated. | Add only unique, indexable, self-canonical routes after their SSR/static pages are live; maintain accurate `lastmod`. |
| Canonical host | Warning | Confirmed | `www` is a separate HTTP 200 host rather than a permanent redirect. | `https://www.offersteady.com/` returned 200; it did not redirect to non-www. | Creates an avoidable duplicate host even though HTML canonical partially mitigates it. | 301 redirect all `www` requests to the equivalent non-www URL. |
| Structured data | Warning | Confirmed | No JSON-LD was detected. | Parser returned zero schema blocks for homepage and all sampled policy/commercial pages. | Search engines and AI systems have weaker entity, product, offer, and breadcrumb understanding. | Add truthful `Organization`, `WebSite`, `SoftwareApplication`, `Offer`, and `BreadcrumbList`; add `Article` only to real editorial guides. Do not invent ratings. |
| Homepage content | Warning | Confirmed | The homepage is too thin and generic for a competitive category. | Parsed word count was 157 (readability extractor: 128); H1 does not contain the product category. | Weak topical coverage, low long-tail reach, and few self-contained passages for AI citation. | Expand with concise product definition, audience, workflow, supported platforms, privacy boundaries, FAQ, and internal links. |
| Trust/content | Warning | Confirmed | Product proof and firsthand evidence are limited in server HTML. | No product screenshots were present in the HTML; no public demo, author/reviewer, case study, or verified testimonial was observed. | Reduces conversion, E-E-A-T, and multimodal GEO eligibility. | Add real screenshots/video, named reviewer/author metadata, verified case studies, and dated guides. |
| Social sharing | Warning | Confirmed | Homepage social metadata is incomplete. | `og:image` and `og:url` are absent; OG title is 67 characters. | Weak link previews reduce click-through and brand consistency when shared. | Add a 1200×630 branded image, absolute `og:url`, matching Twitter image/card, and shorter title. |
| Performance | Warning | Likely | Public delivery is slow from the audit location. | Eight homepage requests produced TTFB 1.22–4.40 s, median about 2.75 s. The 455 KB uncompressed main JS transferred as 161 KB gzip and took 14.34 s from the audit location. Server negotiated HTTP/1.1. | Slow discovery and poor first visit experience, especially outside Singapore. | Measure US/UK/AU/CA field data; place public static pages/assets behind a CDN, enable HTTP/2/3, and cache public HTML briefly while isolating API/SSE/WebSocket traffic. |
| Security/trust | Warning | Confirmed | Six common response security headers are absent. | No HSTS, CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, or Permissions-Policy were detected on homepage. | Primarily a security and merchant-trust gap; indirect SEO impact. | Add reviewed headers gradually and regression-test login, microphone, desktop pairing, and payment flows. |
| Search visibility | Warning | Likely | The domain has little or no discoverable footprint in sampled search results. | `site:offersteady.com` and exact-domain/brand queries did not surface OfferSteady in the audit search source. | Organic acquisition and AI citations cannot compound without index presence and external references. | Verify ownership in Google Search Console and Bing Webmaster Tools, submit sitemap, inspect representative URLs, and build legitimate branded mentions. |

## What is already correct

- Pricing server HTML contains `$19.99/week` and `$39.99/month`.
- Refund Policy exists as an independent server-readable page.
- Terms, About, and Contact expose `杭州临平知界智能技术工作室（个体工商户）, based in Hangzhou, China.`
- `contact@oneshowailab.com` is consistent across the reviewed policy/company pages.
- The current copy retains responsible-use boundaries and does not use anti-detection or cheating claims.
- `robots.txt` does not block public pages or OAI-SearchBot through a crawler-specific rule; it inherits the public wildcard allowance.
- Fingerprinted JavaScript/CSS assets use one-year immutable caching and gzip transfer was observed.

## Content and E-E-A-T assessment

The operator and policy foundation is stronger than the content foundation. The public site says what the product is at a high level, but does not yet prove why users or search engines should trust it as an expert source. For this category, the strongest safe path is to publish detailed preparation and product-usage content with verifiable claims, not aggressive promises about interview outcomes.

Recommended content clusters:

- Real-time AI interview assistant: how audio, transcription, question recognition, and grounded guidance work.
- Interview preparation: behavioral, technical, coding, system design, and role-specific preparation.
- Resume-aware guidance: how Resume/JD context is used and how users should verify claims.
- Screen Assist: supported question types, limitations, privacy boundary, and responsible use.
- Troubleshooting: macOS/Windows setup, meeting audio, microphones, permissions, and connection checks.
- Trust: security, data minimisation, retention, account deletion, availability, refunds, and support.

## GEO assessment

Directional GEO readiness: **22/100 — low**.

The main blockers are the broken discovery endpoints, lack of unique server-readable feature/guide/topic pages, lack of structured data, thin answer passages, and weak external brand/entity signals. `robots.txt` is not the blocker.

AI-citable pages should use question-led H2s, answer the question directly in the first sentence, keep each section self-contained, cite primary sources where factual claims are made, and expose visible update/reviewer information. This should be implemented in normal HTML first; `llms.txt` is a supporting discovery aid, not a replacement for indexable content.

## Environment limitations

- Google PageSpeed Insights returned an API rate-limit error, so no lab Lighthouse or CrUX values are claimed.
- The audit location is not representative of all target users in the United States, United Kingdom, Australia, and Canada; production TTFB findings require regional field verification.
- No Search Console, Bing Webmaster, GA4, backlink database, or server log access was used.
- Visual automation could not run because Playwright was unavailable; mobile layout findings remain unassessed in this report.
