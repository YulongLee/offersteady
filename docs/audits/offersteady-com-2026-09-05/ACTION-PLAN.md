# OfferSteady International SEO/GEO Action Plan

Date: 2026-09-05  
This plan changes only the public international Web/discovery surface. It should not alter login, interview, Companion, ASR, RAG, AI, payment, or API behavior.

## P0 — restore trustworthy crawling before publishing more content

1. Give `/features`, each `/features/*` route, `/guides`, `/interview-questions`, and every future guide/topic a unique server-readable HTML document with its own title, description, canonical, H1, body, and internal links.
2. Add exact Nginx/static mappings before the SPA fallback. Make unknown routes return a real HTTP 404.
3. Serve valid `/llms.txt`, `/llms-full.txt`, and `/public-facts.json` with correct MIME types. Add automated production checks that reject homepage fallback content.
4. Return `noindex, nofollow` for `/login`, `/app`, admin, account, checkout, and other authenticated/non-search routes in the initial response.
5. Permanently redirect `www` to non-www and preserve the full path/query.
6. Rebuild `sitemap.xml` from the actual indexable-route catalogue; include only HTTP 200, unique, self-canonical pages and maintain `lastmod`.
7. Validate with raw `curl` and a parser before deployment; do not validate only React navigation.

Acceptance checks:

- Every indexable URL has a unique title, description, canonical, H1, and substantive body before JavaScript.
- Every non-indexable product route emits a server-visible noindex signal.
- An arbitrary unknown URL returns 404.
- GEO files do not contain `<!doctype html>` and use `text/plain` or `application/json`.
- Sitemap URL set exactly matches the intended indexable catalogue.

## P1 — establish the minimum searchable product surface

1. Expand the homepage from its current 157 parsed words to a concise but substantive product page. Lead with `AI interview assistant` and explain who it is for, what it does, how it works, platforms, privacy, limitations, and responsible use.
2. Publish three initial feature pages: real-time guidance, Resume/JD-grounded answers, and Screen Assist. Each page must answer a distinct search intent and include real product evidence.
3. Publish high-intent guides: behavioral interview preparation, technical interview preparation, coding interview preparation, STAR answers, and audio/device setup.
4. Add visible FAQs as normal HTML. Use schema only where it accurately describes visible content and is eligible.
5. Add consistent navigation, breadcrumbs, and contextual links from guides to features and from features to Pricing/Download.
6. Add a genuine product screenshot set and a short captioned demo video. Do not claim unsupported latency, compatibility, accuracy, or outcomes.

## P1 — entity and structured data

1. Add homepage `Organization` + `WebSite` + truthful `SoftwareApplication` JSON-LD.
2. Add `Offer` data that matches visible Pricing exactly; while checkout is closed, do not mark paid offers as available for purchase.
3. Add `BreadcrumbList` to feature, guide, and topic pages.
4. Add `Article` only to real editorial pages, including author/reviewer and published/updated dates.
5. Add `sameAs` only for official profiles actually controlled by OfferSteady.

## P1 — measurement and submission

1. Verify `offersteady.com` in Google Search Console and Bing Webmaster Tools.
2. Submit `https://offersteady.com/sitemap.xml` to both.
3. Inspect `/`, `/pricing`, one feature page, and one guide URL after the crawl fixes.
4. Configure GA4 or a privacy-compatible analytics layer with conversion events: landing view, pricing view, download click, sign-up, Companion connected, first session, checkout start, and paid conversion.
5. Configure rank monitoring for brand and non-brand queries by US, UK, CA, and AU rather than combining all countries.

## P2 — performance and security

1. Measure production from US-East/West, London, Toronto, and Sydney. Use CrUX/Search Console field data when enough traffic exists.
2. Put public HTML and fingerprinted static assets behind a CDN. Keep API, SSE, WebSocket, and authenticated traffic outside unsafe caches.
3. Enable HTTP/2 or HTTP/3 at the public edge. Keep Brotli/gzip and immutable asset caching.
4. Add HSTS, nosniff, referrer policy, frame protection, permissions policy, and a tested CSP in stages.
5. Add a 1200×630 social image, `og:url`, and Twitter large-image card.

## P2 — authority and GEO growth

1. Create official OfferSteady profiles on LinkedIn and YouTube, then link them consistently from Organization schema and About.
2. Publish demo/setup videos that show real product operation and responsible-use boundaries.
3. Publish real case studies and testimonials only with user consent and verifiable context.
4. Add author/reviewer pages for people who actually maintain interview and technical content.
5. Earn relevant mentions through launch directories, partner content, technical explainers, and genuine community participation; do not manufacture reviews or spam Reddit.

## Information required from the owner

The following inputs are needed before high-quality SEO/GEO content can be completed:

- Approved English legal name/transliteration and the public business address format.
- Primary market order: US, UK, Canada, Australia, and any excluded jurisdictions.
- Precise supported OS versions, CPU architectures, browsers, and conferencing platforms.
- Verified product facts: free allowance, feature limits, data retention, transcript/audio storage policy, account deletion process, and support response time.
- Final Creem billing rules once approved: renewal, cancellation, taxes, refund window, and entitlement behavior.
- Original product screenshots and a permission-safe demo recording.
- Founder/team/editor names, bios, relevant experience, and official LinkedIn profiles.
- Three to five real user stories or testimonials with consent; zero is better than fabricated proof.
- Google Search Console, Bing Webmaster Tools, and analytics ownership/access.
- Official OfferSteady social/profile URLs and a brand social-share image.
- A ranked keyword/business priority list: live interview guidance, interview preparation, coding interviews, Screen Assist, resume-aware answers, or another primary category.

## Safe rollout sequence

1. Snapshot the current production Web release.
2. Implement and test P0 in an isolated international Web build.
3. Verify every URL with `curl`, HTML parsing, 404/noindex tests, sitemap comparison, and structured-data validation.
4. Deploy only static Web/Nginx changes during a low-traffic window; do not rebuild or restart Backend/PostgreSQL/Redis/Companion services.
5. Smoke-test login and interview entry after deployment.
6. Submit the corrected sitemap only after production verification passes.

