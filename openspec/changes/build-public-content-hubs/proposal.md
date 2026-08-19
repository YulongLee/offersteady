## Why

The public site now answers several commercial and setup questions, but visitors and crawlers still lack clear top-level entry points for product capabilities, interview guidance, and interview-question topics. Establishing three truthful content hubs creates the information architecture needed for future SEO/GEO articles without changing the authenticated product or publishing empty, low-value pages.

## What Changes

- Publish server-rendered public hub pages at `/features`, `/guides`, and `/interview-questions` with unique intent, substantive introductory content, and crawlable links to existing canonical pages.
- Keep `/guide` as the product usage manual while `/guides` becomes the editorial interview-guidance directory.
- Update public navigation, footer, sitemap, GEO discovery files, canonical metadata, structured data, and explicit Nginx routes so the hubs are consistently discoverable.
- Extend deterministic source/build verification and route smoke coverage from 17 to 20 public canonical routes.
- Preserve all authenticated application, interview, realtime audio, screenshot, knowledge-base, billing, membership, admin, and desktop behavior.
- Do not create empty blog, comparison, or child-topic pages; those require separate content changes with substantive reviewed content.

## Capabilities

### New Capabilities

- `public-content-hub-navigation`: Public visitors and crawlers can enter distinct product-feature, interview-guide, and interview-question content trees through stable, indexable hub pages.

### Modified Capabilities

None.

## Impact

- Web public assets: three static HTML hub documents, shared styles, homepage and public-page navigation/footer links, sitemap, `llms.txt`, `llms-full.txt`, `public-facts.json`, and regression tests.
- Ingress: three explicit public route mappings and corresponding structured-data CSP hashes.
- Documentation: public SEO page map and content architecture records.
- No API, database, authentication, user data, prompt, model, payment, interview, realtime, desktop, or deployment-architecture change.
