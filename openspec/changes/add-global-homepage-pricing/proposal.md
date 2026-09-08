## Why

OfferSteady's time-based plans are a meaningful commercial advantage, but homepage visitors currently have to navigate to Pricing before they can see them. A concise homepage pricing section can make the flexible 24-hour, weekly, monthly, and 90-day choices visible at the point where visitors already understand the product.

## What Changes

- Add a polished English pricing section to the Global homepage after the core capabilities and before the responsible-assistance section.
- Show the existing Free allowance and the four current paid prices and terms without introducing a second pricing source of truth.
- Highlight Pro Weekly as the existing featured plan and present clear links to start free or compare complete plan details.
- Add responsive layouts for desktop, tablet, and mobile.
- Keep checkout, entitlement, billing, backend, and China-site behavior unchanged.

## Capabilities

### New Capabilities

- `global-homepage-pricing`: Covers homepage pricing visibility, source consistency, conversion copy, navigation, and responsive presentation.

### Modified Capabilities

None.

## Impact

- Affects Global homepage markup, styles, and UI regression tests in `apps/web-global`.
- Reuses `public-review-pages.json`, which already drives the canonical public Pricing page, so prices and plan benefits are not independently duplicated.
- Adds no API calls, runtime dependency, payment activation, entitlement changes, database changes, or China-site changes.
