## Context

The Global homepage currently progresses from product introduction and film to workflow, capabilities, and responsible-use information. The canonical public plan catalogue already defines Free, Interview Day Pass, Pro Weekly, Pro Monthly, and Job Hunt with approved prices, terms, benefits, and featured state. Checkout availability is managed separately and must not be implied by a homepage presentation change.

## Goals / Non-Goals

**Goals:**

- Make OfferSteady's flexible time-based pricing visible on the homepage without overwhelming the page.
- Emphasise that visitors can choose access matching one interview day through a 90-day search.
- Keep all displayed prices and benefits consistent with the existing public Pricing page.
- Preserve fast rendering and usable mobile layout.

**Non-Goals:**

- Activating or changing Creem checkout, billing modes, subscriptions, entitlements, taxes, refunds, or plan definitions.
- Adding urgency, discounts, savings claims, customer counts, testimonials, or other claims without evidence.
- Changing the China homepage or any authenticated product workflow.

## Decisions

1. Place pricing after core capabilities and before responsible assistance. Visitors first understand the product and then see purchase choices before reviewing trust boundaries. Putting five cards directly after the hero was rejected because it would compete with the product film and make the first screen feel transactional.
2. Read the Pricing page record through `publicReviewPage("pricing")` and render its existing plan objects. A separately hard-coded homepage price array was rejected because prices could drift.
3. Present Free as a compact introductory strip and the four paid options as the primary grid. This keeps the paid comparison scannable while preserving the visible $0 entry point.
4. Use the headline “Pay for the time you need.” and supporting copy focused on scheduling flexibility. Avoid “cheapest,” “best,” savings percentages, or urgency claims because they are not substantiated.
5. Link the section to `/pricing` for complete disclosures and `/login` for the existing free start path. Plan cards themselves do not initiate checkout, so this change cannot alter payment behavior.

## Risks / Trade-offs

- [Five options can make the homepage dense] → Use a compact Free strip, four paid cards, concise benefits, and responsive stacking.
- [Catalogue content may be unexpectedly absent] → Render the section only when the canonical Pricing record includes plans and cover the expected catalogue with regression tests.
- [Pricing may change later] → Consume the same public catalogue used by `/pricing`; one data edit updates both surfaces.
- [Visitors may assume checkout is available] → Route to the full Pricing page, where current availability and commercial disclosures remain authoritative.

## Migration Plan

1. Use `global-homepage-film-20260907.1` as the immutable production baseline and verify that the scoped source difference contains only the approved homepage pricing markup and styles.
2. Re-run the Global Web regression suite, English-copy audit, typecheck, production build, and strict OpenSpec validation.
3. Wait until recent live interviews, active desktop transports, realtime workers, and queued frames are all zero.
4. Create a new release, retain the existing Global Web image as a rollback tag, and recreate only Global Web.
5. Verify the public build marker, homepage bundle pricing markers and navigation, health endpoints, logs, and unchanged Global core and China service identities.
6. If verification fails, restore the preceding release symlink and retained Web image without restarting core services.

## Open Questions

None.
