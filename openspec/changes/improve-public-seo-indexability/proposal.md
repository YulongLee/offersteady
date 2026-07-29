# Proposal: Improve public SEO indexability

## Why

The public site currently sends the same indexable SPA shell for valid routes, SEO control files, and unknown URLs. Search crawlers therefore cannot reliably distinguish the homepage, application routes, and missing pages, while the homepage's existing product content is unavailable without JavaScript execution.

## What Changes

- Restrict SPA fallback to the product's known browser routes and return a real 404 for unknown paths.
- Publish valid `robots.txt` and `sitemap.xml` resources.
- Redirect the `www` host to the apex host and declare the homepage canonical URL.
- Include the existing homepage value proposition, workflow, pricing model, privacy summary, internal links, and truthful product schema in the initial HTML.
- Add deterministic regression checks for these P0 crawlability requirements.

## Non-Goals

- No visual redesign or product-flow change.
- No changes to authentication, interviews, materials, realtime audio, billing, payments, or desktop companions.
- No new public content pages, route-level code splitting, social sharing metadata, or search-console integration in this change.

## Capabilities

### New Capabilities

- `public-search-indexability`: deterministic public crawl, canonical, sitemap, robots, and initial-HTML behavior.

### Modified Capabilities

- `containerized-deployment-baseline`: Nginx preserves known SPA routes while rejecting unknown routes.
