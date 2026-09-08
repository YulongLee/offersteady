# Domestic homepage download refinement — local only

Owner cancelled rollback before any production write and requested refinement of the current homepage download area. Production remains `cn-home-commercial-20260907.1`; this follow-up is not deployed.

## Implementation

Worktree: `/private/tmp/offersteady-cn-release-20260907.DTlvCc` (the deployed homepage baseline, not stale main workspace App).

Changed `apps/web/src/App.tsx`, `homepage-commercial.css`; added `HomepageDownloads.tsx`. Existing domestic `state.releaseManifest` and `downloadableRelease` rules provide installer links. Windows links directly; native Mac disclosure exposes Apple Silicon/Intel/Universal as available. Missing, invalid and withdrawn releases cannot be downloaded. No new network calls, dependency changes, backend/core/international edits or hardcoded installer versions.

Page-cro skill informed contrast, concise controls and primary/secondary action hierarchy; international download appearance was reused, not international release URLs. OpenSpec apply skill used existing `optimize-cn-homepage-commercial-clarity` follow-up tasks. Footer guide remains accessible; only redundant hero resource links were replaced. Compliance note retained.

## Verification

- 372 tests passed, 0 failed (JSON `/private/tmp/cn-home-download-tests.json`). Added six download tests and adjusted guide navigation assertions to its retained footer location.
- Typecheck and production build passed. Known existing SEO bundle-budget issue remains; icon/component addition increases entry bundle from ~429 KB to ~442 KB (about 3.4 KB gzip additional JS), no performance improvement claimed.
- Local synthetic preview at 1440/900/390/320: no horizontal overflow; Mac menu remains within viewport. Space opens, Escape closes/refocuses. Initial 320px menu clipping fixed with scoped two-column buttons. No real installer downloaded in tests; link targets verified against supplied manifest fixtures.
- Screenshots: `design/previews/cn-home-downloads/`, including `hero-390.png`, `mac-open-320.png` and `measurements.json`.
- Local preview fixture explicitly supplies a synthetic Windows download; it is not a production entrypoint or release asset.

## Handoff

Deploy only on subsequent owner authorization, from current production baseline, after idle checks. Required source overlay: App.tsx, homepage-commercial.css, HomepageDownloads.tsx. Do not deploy synthetic preview or unrelated dirty changes. Source/tests/spec snapshot preserved in `design/previews/cn-home-downloads/source-overlay.tgz`.
