# OfferSteady International Post-Deployment Action Plan

Date: 2026-09-05  
Scope: Recommendations only. No production changes were made during this audit.

## P0 — current blockers

No confirmed availability, indexing, 5xx, broken-link, schema, GEO-file, sitemap, canonical-host, or unknown-route blocker was found.

## P1 — next performance and conversion release

1. Preserve UTM/query parameters during trailing-slash redirects. This is a small, isolated ingress correction and should be regression-tested before deployment.
2. Make `/download` actionable. Use approved direct installers or a clear sign-in path; do not publish stale or unsigned artifacts.
3. Compress the 772 KB social share image.
4. Add regional monitoring before making infrastructure claims: public TTFB and CWV in US East/West, London, Toronto, and Sydney.
5. If regional measurements confirm origin delay, add a CDN only for public HTML and fingerprinted assets. Explicitly bypass `/api/`, realtime streams, WebSocket routes, `/login`, `/app`, and user-specific responses.

## P1 — searchable content and proof

1. Expand the four feature pages from roughly 328–399 words into complete, distinct product explanations with real screenshots and accurate limitations.
2. Publish a small reviewed guide set rather than many thin pages: behavioural answers, technical interviews, coding workflow, system design, and Companion audio/setup troubleshooting.
3. Add a named author or reviewer only after the owner approves a real identity and relevant biography.
4. Add a permission-safe product demo and genuine user evidence. Do not fabricate ratings, outcomes, accuracy, latency, integrations, or testimonials.
5. Simplify difficult homepage sentences while preserving the responsible-use language.

## P2 — metadata, entity, and measurement

1. Improve the four short titles and two short meta descriptions without changing promises.
2. Create `support@offersteady.com` or `contact@offersteady.com` as an alias if the owner wants stronger domain-level trust; keep `contact@oneshowailab.com` until the new mailbox is proven operational.
3. Add official `sameAs` profiles only after real OfferSteady profiles exist.
4. Verify or connect Google Search Console and Bing Webmaster Tools, submit the existing sitemap, and inspect `/`, `/pricing`, `/features`, and one guide URL.
5. Add privacy-reviewed measurement for landing view, pricing view, download action, registration, Companion connection, first session, checkout start, and paid conversion.

## Owner inputs required

- Approved installer URLs, supported OS versions, CPU architectures, signing/notarisation status, and update policy.
- Real product screenshots and a safe demonstration recording.
- Approved public founder/editor identity and biography, if one will be published.
- Official OfferSteady social URLs.
- Search Console, Bing, analytics, and regional performance access.
- Confirmation on whether a domain-matching support mailbox can be created.
