## Context

The Global backend is configured for Creem Live and exposes five published plans. The authenticated billing page already performs the real checkout request, but the static homepage and `/pricing` documents were generated while merchant review was pending. Their disabled buttons and “checkout unavailable” disclosures are now stale.

## Goals / Non-Goals

**Goals:**

- Make public Global pricing copy and structured data match the live commerce configuration.
- Give anonymous visitors a clear sign-in path for paid plans without exposing secrets or bypassing authentication.
- Preserve dynamic checkout and payment confirmation behavior.

**Non-Goals:**

- No changes to Creem API calls, webhook verification, order state transitions, prices, or entitlements.
- No automatic checkout, simulated payment, or anonymous order creation.
- No changes to the Chinese edition.

## Decisions

1. **Use `/login` as the public CTA target.** Checkout requires an authenticated account; linking to the existing login route keeps the current security boundary and avoids duplicating checkout logic in static HTML.
2. **Keep plan values server-authoritative at runtime.** Public catalogue content is updated from the approved production plan configuration and the authenticated billing page continues to load `/api/v1/global-commerce/catalogue`; no client-side payment credentials are introduced.
3. **Regenerate static pages from the catalogue source.** Updating the existing JSON source and running its generator keeps page copy, JSON-LD, and tests consistent instead of hand-editing generated HTML.

## Risks / Trade-offs

- [Static pages can drift from a future provider toggle] → Keep the deployment checklist tied to the live readiness endpoint and rerun static generation whenever commerce availability changes.
- [Anonymous visitors may expect checkout before signing in] → CTA copy explicitly says “Sign in to choose a plan”; the existing authenticated flow remains unchanged.

## Migration Plan

1. Update the Global public catalogue copy and paid-plan links/actions.
2. Regenerate public HTML and run focused and existing Global tests, typecheck, build, and OpenSpec validation.
3. Deploy only the Global Web image after confirming Creem readiness; verify public pages and manifest.
4. Roll back by restoring the previous Web image/release if any public route fails. Do not restart backend or data services.

## Open Questions

None.
