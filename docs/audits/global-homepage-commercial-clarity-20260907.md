# International homepage commercial clarity — 2026-09-07

## Scope and status

Implemented under `optimize-global-homepage-commercial-clarity`. Initially accepted locally; subsequently deployed on explicit owner approval as [global-commercial-20260907.1](../releases/global-commercial-20260907.1.md). This change affects international public-page presentation and generated homepage HTML only; it does not change China, authentication, interviews, Companion, AI, API, entitlements or checkout logic.

Support remains `contact@oneshowailab.com`. Legal operator details, existing policies, prices, allowances and renewal terms are retained. Paid checkout is not activated by this change.

## Audit findings and decisions

- The old hero led with a long explanation and delayed the primary action. Use a concise headline, one benefit sentence, Start free and existing downloads; retain a short responsible-use note after the actions.
- Repeated feature/workflow sections delayed pricing. Consolidate four benefits, retain existing feedback, then show canonical prices before setup videos and comparison.
- Long comparison and multiple video sections made the journey harder to scan. Keep the comparison available in a native disclosure; group the two existing videos in one setup section.
- Add seven FAQs covering free limits, personal context, computer compatibility, renewal, checkout availability, permitted AI use and data handling. Finish with a free-start action.
- Fix the pricing glow's horizontal overflow at intermediate widths; constrain its pseudo-element inside the section. Use responsive footer columns and explicitly hide closed comparison content.

The page-cro and write-landing skills informed hierarchy and copy. OpenSpec proposal/apply skills structured acceptance and implementation. No traffic, conversion baseline or controlled experiment data was supplied; no conversion uplift or performance percentage is claimed. Existing feedback provenance and dated competitor claims are unchanged, not independently re-verified in this task.

## Copy handoff

Headline: **AI interview guidance. Built around you.**

Description: Follow live questions and shape your answers with AI guidance based on your resume and target role.

Primary action: Start free. Secondary action: See how it works.

Short note: Verify AI suggestions and follow your interview organiser's rules.

Full benefits, FAQs and closing copy: [homepage-commercial.json](../../apps/web-global/src/homepage-commercial.json). Canonical pricing/policy source: [public-review-pages.json](../../apps/web-global/src/public-review-pages.json).

## Verification

- `npm run test --workspace @offersteady/web-global`: **88 tests passed, 10 files**.
- `npm run test:copy --workspace @offersteady/web-global`: 648 explicit English entries; copy/route/metadata audit passed.
- Production-mode `npm run build --workspace @offersteady/web-global`: TypeScript and build passed. Vite still reports a main chunk over 500 kB; bundle splitting was not undertaken in this presentation-only change.
- `npm run test:merchant-review --workspace @offersteady/web-global`: 16 indexable URL checks passed.
- `node apps/web-global/scripts/check-review-http.mjs`: local production preview returned 200 and expected independent title, description, H1 and canonical for home, pricing, terms, privacy, refund policy, contact, about and security. Robots and sitemap checks passed. These are **local build checks**, not verification of a new production deployment.
- Static homepage includes shared benefits, pricing, FAQ, support/operator and video content without executing JS. Existing competitor comparison remains a React disclosure; this task does not newly prerender the comparison.
- Chrome screenshots/layout checks at 320, 390, 900 and 1440 px passed: no page/price-card overflow, four benefits, seven FAQs, native disclosure mouse interaction and expanded comparison bounds. Desktop Enter-key disclosure checks also passed; repeated cross-viewport keyboard automation stalled in the test browser, so full mobile keyboard verification is not claimed.
- Both videos remain muted, controls enabled, inline, metadata-preloaded, without autoplay.
- OpenSpec strict validation passed; scenarios covered by regression tests, static HTTP assertions and browser checks.

## Observed layout measurements

Same 1440 px desktop viewport, production baseline versus local synthetic design preview, comparison closed:

| Measurement | Before | After |
| --- | ---: | ---: |
| Homepage document height | 8,223 px | 5,245 px |
| Pricing section document position | 6,349 px | 1,895 px |
| Primary CTA bottom position | 745 px | 474 px |
| Hero description words | 24 | 17 |

These are layout observations, not load-time or conversion measurements. At 390/320 px the primary CTA bottom is about 413/455 px respectively. Full measurements: [measurements.json](../../design/previews/global-home-commercial/measurements.json).

## Screenshots

- [Desktop hero](../../design/previews/global-home-commercial/hero-1440.png)
- [Mobile hero](../../design/previews/global-home-commercial/hero-390.png)
- [Desktop pricing](../../design/previews/global-home-commercial/pricing-1440.png)
- [Mobile setup/videos](../../design/previews/global-home-commercial/tour-390.png)

## Remaining boundaries

Creem production approval/configuration remains a separate prerequisite for real payments. This change does not certify merchant approval or promise higher conversion. After an authorized deployment, recheck real production HTTP and mobile behavior; actual analytics can then inform headline/price-placement experiments. No analytics or experiment dependencies were added.
