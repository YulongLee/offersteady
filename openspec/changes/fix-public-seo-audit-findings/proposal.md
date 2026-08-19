## Why

The public site has a sound crawlability baseline, but the sitemap-listed guide route currently emits the homepage canonical and metadata, while public HTML caching and route-level regression coverage leave avoidable SEO and first-load risks. These issues can reduce indexation and search discoverability even though the product itself works correctly.

## What Changes

- Give the public `/guide` route its own server-delivered title, description, self-canonical, structured data, and crawlable guide summary.
- Add ordinary crawlable links between the homepage and public guide without changing the rendered product journey.
- Improve the homepage search title and structured brand naming while preserving all existing calls to action and product behavior.
- Replace `no-store` on public indexable HTML with revalidation-friendly caching while keeping authenticated and sensitive routes non-cacheable.
- Extend deterministic SEO release checks so every sitemap URL must be successful, indexable, uniquely described, and self-canonical.
- Keep existing product capabilities, authenticated routes, interviews, materials, billing, realtime audio, and desktop companion behavior unchanged.
- Do not add unverified reviews, ratings, customer claims, legal entity details, or new marketing statistics.

## Capabilities

### New Capabilities

- `public-seo-quality`: Covers route-specific public metadata, canonical consistency, crawlable navigation, truthful structured data, public HTML caching, and release-time sitemap validation.

### Modified Capabilities

None.

## Impact

- Affected Web files: public entry documents, public route title handling, sitemap metadata, SEO regression scripts, and Vite multi-page build configuration.
- Affected ingress files: Nginx handling for the homepage, public guide, and authenticated/noindex HTML caching.
- No API, database, authentication, payment, interview, realtime, material, or desktop protocol changes.
