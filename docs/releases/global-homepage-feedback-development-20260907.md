# Global homepage feedback — development only

## Scope

The owner supplied 20 Chinese feedback entries and a poster, asserted they were authentic, and requested anonymous English homepage presentation. The implementation faithfully translates those entries; no independent authenticity verification was performed. Poster identities, photographs, job titles, likes, stars and employer/offer claims were not added. Original criticism and requests for future features remain intact. English disclosure states that submissions were translated and experiences/plans can differ by edition, so regional pricing comments are not assertions about current Global prices.

The module sits between comparison and pricing, uses the existing dark/mint design, and displays three/two/one cards at desktop/tablet/mobile widths. Automatic rotation advances one entry every 10 seconds only while visible. Hover temporarily pauses it; keyboard focus, manual navigation, swiping and explicit pause stop it until Play is selected. Reduced motion defaults to paused. Previous/next wrap through every entry. An expandable no-JavaScript section shares the same JSON catalogue.

No production deployment, server action, new dependency, API request, backend, China-site, pricing, login or interview behavior change was made.

## Verification

- `npm --workspace @offersteady/web-global test`: **72 passed**, 8 files (13 new cases including homepage integration).
- `npm --workspace @offersteady/web-global run test:copy`: passed, 648 explicit copy entries.
- Production build with `VITE_APP_ENV=production VITE_API_BASE_URL=/ VITE_PUBLIC_APP_VERSION=global-feedback-preview-20260907.1`: passed, including TypeScript.
- `npm --workspace @offersteady/web-global run test:merchant-review`: passed, 16 indexable URLs.
- Built `dist/index.html` includes all 20 quotes and the edition note; no review/aggregate-rating schema added.
- `openspec validate add-global-homepage-feedback --strict`: passed.
- Local headless Chrome: 1440/900/390/320px layouts tested across all 20 positions. No feedback-section overflow or Chinese text. Real pointer Play advances after 10 seconds; Pause holds for a further 10 seconds.
- Existing whole-page overflow remains at 900px (914px page width) and 320px (343px page width), unchanged when the new module is hidden. This pre-existing issue is not fixed in this scoped change. At 1440px and 390px the whole page fits.
- Existing main-chunk warning persists. Local main JS is approximately 161.50 kB gzip; no performance improvement claim is made. Feedback uses text and existing icons, no third-party requests, photos or analytics.

## Review assets

- [Desktop](../../design/previews/global-feedback/1440.png)
- [Tablet](../../design/previews/global-feedback/900.png)
- [Mobile](../../design/previews/global-feedback/390.png)
- [Narrow mobile](../../design/previews/global-feedback/320.png)

## Future deployment boundary

Do not deploy the dirty workspace wholesale. Before any future release compare against the then-current Global server baseline, package only approved Global changes, rerun verification and retain rollback. This development adds the feedback component, scoped CSS and JSON catalogue; integrates it into App; adds generation logic and an index marker; and adds tests/specs. The current source generator and homepage must be included together to preserve the static fallback.
