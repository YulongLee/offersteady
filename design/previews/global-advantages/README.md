# Global homepage advantages — local design review

Local preview: http://127.0.0.1:5273/design-preview.html

Placement: after Core Capabilities and before existing homepage pricing. Following the user's correction, the DIY comparison was replaced with actual anonymised Product A/B/C peers using official-source research. Price/term comparison leads, followed by shared capabilities. No lowest-price, performance, savings or stealth claims. Internal source mapping and uncertainties: [research note](../../../docs/global-comparison-research-20260907.md). That note is not imported into public assets. Canonical OfferSteady prices are reused rather than redefined.

Desktop screenshot: [desktop.png](./desktop.png). Phone screenshot: [mobile.png](./mobile.png).

Verified with actual Chrome at 1440px and 375px after redesign. Phone rows become cards labelling OfferSteady and each peer explicitly. Page widths match both viewports without horizontal overflow. Tests: 57 passed; English-copy audit, typecheck/build and strict OpenSpec validation passed. Local preview uses only an existing synthetic test fixture; its HTML is not a production build entry and was verified absent from dist. No production API is used for preview initialization. Competitor capability listings are not claims of equal performance or inclusion in every tier; anonymous draft remains subject to owner review and fresh verification before publication.

September 7 approved publication revision: eight feature rows precede one grouped pricing row; one compact day-pass callout leads. Real competitor names are now partially masked consistently in headers and mobile cards. The user approved Global Web deployment; only App.tsx, HomepageAdvantages.tsx and styles.css are overlaid on the current production baseline. Local-only preview entry and test fixture must not be published. See the release record for actual deployment status.
