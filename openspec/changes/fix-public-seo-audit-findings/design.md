## Context

The Web client is a Vite React SPA behind an explicit Nginx route allowlist. The homepage currently has a crawlable static fallback, while `/guide` is served from the same `index.html`; as a result, crawlers receive the homepage title, canonical, and structured data for the guide. Public and authenticated HTML also share a `no-store` policy even though only authenticated routes require that strict behavior.

The implementation must improve public discovery without changing React route behavior, authentication, product state, API contracts, or the visible interview workflow.

## Goals / Non-Goals

**Goals:**

- Make every sitemap URL return route-specific, self-canonical server HTML.
- Preserve the existing React guide after JavaScript starts.
- Improve homepage search-result context without changing calls to action or product behavior.
- Let browsers revalidate public HTML while retaining `no-store` for login and authenticated routes.
- Block releases when sitemap URLs and their metadata disagree.

**Non-Goals:**

- No changes to interviews, realtime audio, screenshots, materials, billing, payments, authentication, or desktop behavior.
- No new analytics, external SEO service, runtime dependency, or user tracking.
- No invented reviews, ratings, legal entity details, performance claims, or customer data.
- No broad visual redesign or route-level application code splitting.

## Decisions

### Build a dedicated guide entry document

Vite will use explicit multi-page inputs for `index.html` and `guide.html`. Both entries start the same React application, but `guide.html` carries guide-specific static content and head metadata. Nginx serves `guide.html` only for `/guide`.

This is preferred over Nginx `sub_filter`, which would make metadata fragile, and over client-only `document.title`, which does not fix raw HTML canonical signals. It also avoids introducing an SSR framework solely for one public route.

### Keep product routing unchanged after hydration

The guide entry loads the existing `src/main.tsx`; BrowserRouter reads `/guide` and renders the existing `GuidePage`. Runtime title effects will be route-aware so the application does not overwrite guide or legal-page titles with the homepage title.

### Use truthful route-specific structured data

The homepage keeps its existing entity graph. The guide adds `WebPage` and `BreadcrumbList` data referring to the existing website entity. No rating, review, price, customer, or unverified legal entity data is introduced.

### Split public and private HTML caching

The homepage and public guide use `public, max-age=0, must-revalidate`, allowing storage while requiring freshness checks. Login, invitation, legal, error, and authenticated application routes retain `no-store` and their existing index controls. Fingerprinted assets remain immutable.

### Validate the production artifacts, not only source templates

The SEO regression script will inspect both entry documents, sitemap URLs, route mappings, index controls, and cache policies. A post-build assertion will confirm that `dist/index.html` and `dist/guide.html` exist with distinct self-canonicals.

## Risks / Trade-offs

- [Two HTML entry files can drift] → Keep shared product facts deliberately small and cover titles, canonicals, schemas, links, and build outputs with deterministic tests.
- [Multi-page Vite output can duplicate module entry references] → Both pages import the same application entry so Rollup can share hashed chunks; verify bundle output and smoke-test both routes.
- [Public revalidation could serve stale HTML if an intermediary ignores directives] → Use max-age zero plus must-revalidate, keep hashed assets immutable, and retain the build manifest/version-refresh safeguards.
- [Changing the homepage title can affect brand-result appearance] → Preserve “面试稳” in the title and keep the visible H1 and page copy unchanged.

## Migration Plan

1. Build and test both entry documents locally.
2. Validate Nginx syntax and run route-level HTTP checks against the production container configuration.
3. Deploy the static bundle and Nginx configuration together.
4. Roll back both artifacts together if `/guide` or the homepage fails; no database migration is involved.

## Open Questions

- The exact registered legal operator name must be confirmed before adding `legalName` to structured data or replacing the existing footer attribution.
- Existing marketing metrics require a documented source and calculation method before they can be strengthened as E-E-A-T evidence.
