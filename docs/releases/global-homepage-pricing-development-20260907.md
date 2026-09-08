# Global homepage pricing development handoff 2026-09-07

- Status: superseded by deployed release `global-homepage-pricing-20260907.1`
- Production baseline: `global-homepage-film-20260907.1`
- Scope: Global homepage UI only
- Backend, checkout, entitlement, billing, database, Companion, interview flow and China site: unchanged

## Homepage structure

The pricing section sits after Core Capabilities and before Responsible Assistance:

1. Eyebrow: `FLEXIBLE ACCESS`
2. Headline: `Pay for the time you need.`
3. Supporting message: `One interview tomorrow or a full job-search season—choose 24 hours, 7 days, a month, or 90 days. No annual commitment.`
4. Compact Free entry strip with the existing `$0` allowance and Start free action.
5. Four paid-plan cards for Interview Day Pass, Pro Weekly, Pro Monthly, and Job Hunt. Pro Weekly uses the canonical featured state.
6. Compare all plans action linking to `/pricing`, followed by availability, renewal, and refund disclosure guidance.

The homepage reads plan names, prices, terms, benefits, and featured state from the same `public-review-pages.json` record used by `/pricing`; there is no second homepage price list.

## Verification

- Focused Global product test: 49 passed.
- Full Global Web suite: 55 passed.
- English-copy, route, and public metadata audit passed with 660 explicit entries.
- TypeScript and production Vite build passed.
- Regression coverage verifies all five plan names, exact prices and terms, canonical benefits, Pro Weekly featured state, CTA destinations, and absence of homepage checkout calls.
- OpenSpec strict validation passed.

## Deployment

The approved implementation was deployed as `/opt/offersteady-global/releases/20260907-global-homepage-pricing-1` after an idle activity gate. See `global-homepage-pricing-20260907.1.md` for production verification and rollback details.
