## Why

The international production site now exposes merchant-review pages correctly, but its search-intent routes, unknown-path handling, and GEO discovery files still fall through to the homepage shell. This prevents reliable indexing and AI citation, creates soft-404 duplicates, and leaves the English site without enough crawlable product context to support launch growth.

## What Changes

- Publish distinct server-readable English pages for the public feature, guide, interview-topic, and download entry points already linked from the homepage.
- Remove the obsolete Global user-manual link rather than republishing the user manual that was intentionally removed from the international product.
- Serve valid `llms.txt`, `llms-full.txt`, and `public-facts.json` resources with verified product facts and correct content types.
- Return real 404 responses for unknown public paths and server-visible `noindex` signals for login and authenticated application routes.
- Align canonical-host redirects, sitemap entries, metadata, JSON-LD, social metadata, public cache policy, and security headers.
- Expand the public homepage and hub content with truthful, responsible-use copy, crawlable links, and citation-ready explanations without changing its approved product behavior.
- Add deterministic source, build, Nginx, SEO/GEO, and production-route regression checks.
- Deploy only the international public Web/ingress surface after verification; preserve the current release as rollback baseline.

## Capabilities

### New Capabilities

- `global-public-search-content`: Crawlable English homepage, feature hubs, guide hubs, topic hubs, and download information with unique intent, metadata, internal linking, responsible-use language, and no international user-manual surface.
- `global-public-geo-discovery`: Consistent AI discovery resources, entity facts, JSON-LD, sitemap membership, canonical URLs, and social discovery metadata for the Global product.
- `global-public-search-delivery`: Exact ingress routing, meaningful status/index controls, canonical-host behavior, cache/security boundaries, and production verification that remain isolated from application and realtime traffic.

### Modified Capabilities

None.

## Impact

- Global Web only: `apps/web-global` public/static HTML, public assets, page generation, metadata, tests, and build output.
- Global ingress only: `infra/nginx/global-web.conf` and `infra/nginx/offersteady.com.conf` public-page routing and canonical host behavior.
- Global deployment verification and SEO/GEO documentation.
- No changes to the Chinese Web, Backend APIs, database, authentication semantics, interview workflows, Companion, ASR, RAG, AI prompts, payments, Creem activation, or user data.
