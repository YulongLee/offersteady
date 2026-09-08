# OfferSteady International Post-Deployment Website Audit

Date: 2026-09-05  
Scope: Full-site, read-only production review of `https://offersteady.com` after release `global-seo-geo-20260905.1`.

## Audit summary

Overall rating: **Needs improvement, with no current critical availability or indexing defect found.** A numeric score is withheld because target-market Core Web Vitals, Search Console, Bing, ranking, and conversion data are unavailable.

The technical crawling foundation is now healthy. All 16 approved sitemap URLs return their own server-readable content, canonicals and structured data; unknown URLs return 404; application routes are noindex; GEO files are valid; internal links are healthy; and the production services show no recent 5xx or backend errors.

The remaining work is primarily growth and conversion work rather than core-product repair:

1. Public delivery is variable outside the Singapore origin and has no CDN.
2. Most feature and information pages are still shallow for competitive non-brand searches.
3. The Download page is informational but has no download or next-step action.

Top opportunities are to isolate public static delivery behind a CDN, add real product proof and deeper reviewed content, and connect search/conversion measurement.

## Current production health

- All six Global containers are running; Backend, PostgreSQL, and Redis report healthy.
- In the reviewed one-hour window, the Global Web emitted 196 HTTP 200 responses and zero 5xx responses; the Global Backend emitted zero detected errors.
- Server-loopback time to first byte was about 1.5–2 ms for public HTML and about 5.5 ms for `/healthz`.
- HTTPS uses TLS 1.3 and HTTP/2; the current certificate expires on 2026-12-03.
- External measurements from the audit location produced 1.09–4.47 s time to first byte. This does not prove the experience in the US, UK, Canada, or Australia, but it shows that the origin path can dominate latency.

## Findings

| Area | Severity | Confidence | Finding | Evidence | Fix |
|---|---|---|---|---|---|
| Public delivery | Warning | Likely | Delivery outside the origin remains slow and variable. | External TTFB was about 1.09–4.47 s while the same HTML took about 1.5–2 ms on origin loopback. DNS points directly to the Singapore host. A main-JS transfer also stalled in the audit location. | Cache only public HTML and fingerprinted assets at an edge CDN; bypass API, SSE, WebSocket, login, and app traffic. Add US/UK/CA/AU synthetic and real-user CWV measurement. |
| Content depth | Warning | Confirmed | Most indexable pages are too shallow to compete for non-brand intent. | Fourteen of 16 sitemap pages contain fewer than 400 parsed words; the four detailed feature pages contain 328–399 words. Only guide/topic hubs are published. | Expand a small number of high-intent pages with distinct, reviewed, answer-first content, real examples, update dates, and contextual links. |
| Trust and E-E-A-T | Warning | Confirmed | The policy foundation is stronger than the firsthand product evidence. | The 16 initial HTML documents contain no visible content images. No public product demo, case study, verified testimonial, named author/reviewer, official social profile, or source citation was found. | Add genuine screenshots/demo media, responsible-use captions, named maintainers, and only verified evidence and official profiles. |
| Download conversion | Warning | Confirmed | `/download` is a dead end for high-intent visitors. | It contains navigation, policies, and support email only; there is no installer link and no sign-in/start action. | Publish verified installer actions when ready, or route users clearly to sign in and retrieve the supported release. |
| Attribution | Warning | Confirmed | Trailing-slash redirects discard campaign parameters. | `/features/?utm_source=test` redirects to `/features`; `/pricing/?x=1` redirects to `/pricing`. HTTP and `www` canonical redirects preserve the query correctly. | Preserve the query string during trailing-slash normalisation and add UTM regression tests. |
| Metadata | Warning | Confirmed | Several snippets are shorter than current quality targets. | Pricing, Privacy, Refund Policy, and Security titles are under 30 characters; Pricing and Contact descriptions are under 120 characters. All remain unique and no title is too long. | Rewrite only these short fields with accurate intent language. |
| Asset size | Warning | Confirmed | The social preview image is heavier than necessary. | The 1200×630 share image is 772,542 bytes. | Compress it while preserving dimensions and visual quality. |
| Measurement | Info | Likely | Organic and conversion performance cannot yet be evaluated. | No public GA/Search Console/Bing tag was detected; DNS verification and private/server-side analytics were unavailable. | Confirm existing ownership or connect Search Console, Bing Webmaster Tools, and privacy-reviewed analytics. |

## Confirmed passes

- All 16 sitemap URLs return HTTP 200, one H1, a unique self-canonical, and valid JSON-LD in initial HTML.
- Homepage metadata is complete; social metadata checks scored 85/100, with only optional Twitter account fields absent.
- `llms.txt` scored 100/100 and `llms-full.txt` exists.
- Security header checks scored 100/100. `includeSubDomains` is intentionally not recommended until every subdomain is verified HTTPS-safe.
- The homepage link check found 16 healthy links, zero broken links, redirects, or timeouts.
- The 17-page internal crawl found no orphan signal at depth one and low duplicate-content similarity after navigation/footer removal.
- Homepage source contains 531 parsed words by the full-page crawler, but readability analysis rated the prose difficult (Flesch 34.5, grade 11.9), so simpler wording remains an engagement opportunity.
- Unknown routes return a real 404 with `noindex,nofollow`; `/login` and `/app` return `noindex,nofollow` and `no-store`.
- `www` and HTTP canonical redirects preserve path and query.
- The sitemap contains exactly 16 canonical URLs and 16 `lastmod` values.

## Unknowns and limitations

- Google PageSpeed Insights was rate-limited after its built-in retry, so no Lighthouse or CrUX value is claimed.
- Search Console, Bing Webmaster Tools, analytics, rankings, backlinks, and conversions were not accessible.
- The in-app browser was unavailable, so this run could not capture and accept desktop/mobile screenshots. Responsive reflow, visible CTA hierarchy, keyboard operation, focus states, contrast, CLS, and INP remain unverified rather than passed.
- External latency was measured from the current audit location, not the four intended markets.
- AI crawler rules inherit `User-agent: *` and are therefore allowed on public routes. Their absence as explicit entries is a policy choice, not a crawl blocker.
