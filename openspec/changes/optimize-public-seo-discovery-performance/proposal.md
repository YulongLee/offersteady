# Proposal: Optimize public SEO discovery performance

## Why

The public crawlability baseline is now correct, but authentication and application routes still expose an indexable response, fingerprinted assets do not advertise immutable caching, and shared homepage links lack standard social preview metadata.

## What Changes

- Mark login, error, and authenticated application routes as `noindex, follow` at the ingress.
- Serve fingerprinted public assets with a one-year immutable cache policy.
- Add complete Open Graph and Twitter Card metadata to the homepage.
- Export the existing approved 1200x630 share-card design as a PNG for consistent social-platform support.
- Extend deterministic SEO regression checks for these response and metadata contracts.

## Non-Goals

- No visual redesign or product-flow change.
- No route-level code splitting in this change.
- No new public landing pages, guides, analytics scripts, or Search Console credentials.
- No changes to authentication, interviews, materials, realtime audio, billing, payments, or desktop companions.

## Capabilities

### Modified Capabilities

- `public-search-indexability`: private application routes are excluded from indexing and the homepage provides standard social metadata.
- `containerized-deployment-baseline`: fingerprinted assets receive an immutable cache policy.
