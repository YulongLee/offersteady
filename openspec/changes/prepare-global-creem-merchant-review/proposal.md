## Why

OfferSteady's Global public pages currently depend on the client router, so direct crawler requests to commercial and legal URLs can receive the home-page HTML instead of page-specific content. Creem review also requires clearly visible pricing, legal documents, support contact information, and a usable refund policy before payment activation.

## What Changes

- Publish a focused Global pricing page for Free, Weekly Pro, and Monthly Pro without enabling checkout.
- Add a standalone refund policy and link it from the public footer.
- Make pricing, legal, company, contact, and security URLs return route-specific initial HTML with unique metadata and substantive content.
- Publish consistent operator identity and support contact details across the required public pages.
- Add and verify Global sitemap, robots, canonical, and page metadata.
- Preserve responsible-use language and the existing application, authentication, interview, Companion, ASR, RAG, AI, and API behavior.

## Capabilities

### New Capabilities

- `global-merchant-review-pages`: Public commercial, legal, company, contact, and security pages required for Global merchant review, including crawler-readable initial HTML and discovery metadata.

### Modified Capabilities

None.

## Impact

- Affects only `apps/web-global` public routes, public page components, static build outputs, Global web-server routing, and focused verification tests.
- Does not add payment calls or change server APIs, authentication, protected application routes, interview flows, desktop Companion, ASR, RAG, or AI behavior.
- No new runtime dependency or sensitive-data processing is introduced.
