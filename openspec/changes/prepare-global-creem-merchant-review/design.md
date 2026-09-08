## Context

The Global web client is a Vite React single-page application. Its web server currently falls back unknown URLs to `index.html`, so direct requests for public commercial and legal routes expose home-page initial HTML and depend on the client router to show the intended page. Creem review requires pricing, legal pages, product clarity, and visible customer support. Payment is not yet enabled.

## Goals / Non-Goals

**Goals:**

- Return route-specific, crawler-readable initial HTML for all required review URLs.
- Keep the browser experience consistent by rendering corresponding React public pages after JavaScript loads.
- Publish accurate pre-payment pricing, refund/support/operator disclosures, sitemap, robots, canonical, and metadata.
- Keep changes isolated to the Global public web surface.

**Non-Goals:**

- Enabling Creem checkout or changing commerce APIs and entitlements.
- Changing authentication, protected application routes, interviews, Companion, ASR, RAG, AI prompts, or API behavior.
- Rebuilding the Global application as a server-rendered framework.

## Decisions

### Generate independent HTML entry documents

Each required public URL will have its own Vite HTML entry generated from a typed/static page catalogue. Every document contains the route-specific title, description, canonical, H1, and substantive body before loading the existing React entry point. Vite builds those entries into `<route>/index.html`.

Alternative considered: runtime SSR. Rejected because it would add a server rendering runtime and deployment complexity to a static Global web container for seven stable pages.

Alternative considered: client-only metadata updates. Rejected because it does not satisfy non-JavaScript crawler access and is the source of the current failure.

### Keep public page facts in one catalogue

Metadata and substantive page sections are defined once and consumed by the static-page generator and the React public-page renderer. This prevents crawler and browser content from drifting.

Alternative considered: hand-maintaining seven unrelated HTML documents and seven JSX pages. Rejected because support email, operator identity, prices, and compliance statements would be easy to make inconsistent.

### Resolve extensionless routes at Nginx

The Global web container will try `<request>/index.html` before falling back to the SPA entry. API, stream, promotion, and asset locations remain unchanged.

Alternative considered: regex rewrites for every page. Rejected because a generic static-entry lookup is simpler, testable, and automatically supports future public entries.

### Treat paid plans as non-interactive before activation

The public Pricing page displays approved products but uses non-checkout Coming Soon controls. Free links to the existing registration route. No commerce endpoint is called or changed.

## Risks / Trade-offs

- [Static HTML and React page content could diverge] → Generate both from the same public-page catalogue and add parity tests.
- [A web-server routing change could affect SPA routes] → Only insert `<route>/index.html` before the existing `/index.html` fallback and retain all API/asset locations.
- [Legal copy can become outdated] → Keep a visible last-updated date and central support/operator constants; obtain legal review before payment activation.
- [A disabled-looking paid CTA may confuse visitors] → Use explicit Coming Soon wording and explain that paid checkout is not yet open.

## Migration Plan

1. Build and test locally without deploying.
2. Verify every required route through the production-like Nginx container or Vite preview using direct HTTP requests with JavaScript disabled.
3. On an approved release window, deploy the static Global web image; no backend migration is required.
4. Roll back by restoring the previous Global web image if route or presentation checks fail.

## Open Questions

- Final legal review of refund eligibility and regional consumer-rights wording remains required before paid checkout is activated.
