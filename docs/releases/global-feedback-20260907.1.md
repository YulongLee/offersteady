# Global homepage feedback release

Deployed to `https://offersteady.com` at approximately 18:31 CST on September 7, 2026 after explicit user approval.

## Scope

Added the 20 owner-supplied feedback translations as the approved anonymous English carousel between comparison and pricing. Retained the translation/edition note and original improvement requests. No invented ratings, likes, identities or review schema added. Source assertions were supplied by the owner, not independently verified.

Only six files were overlaid on the previous server baseline: App.tsx (one import and one section), HomepageFeedback.tsx, homepage-feedback.css, homepage-feedback.json, index.html (static feedback block), and generate-review-pages.mjs (shared-catalogue static rendering). No China, backend, administration, dependencies, payment or authenticated workflow changes.

## Verification

- 72 Global tests in 8 files passed; English copy audit, local production build, merchant-review static checks and strict OpenSpec validation passed.
- Server build passed using the previous successful dependency cache. Existing main-chunk-size warning remains (161.67 kB gzip main JS).
- Idle gates before build and immediately before cutover found zero live sessions, desktop transports, queue workers, pending frames and active answer/screenshot work.
- Only Web recreated. Core container IDs and start times match before/after; health and Nginx config checks passed. First startup probe returned an empty reply; subsequent retries passed.
- Public build manifest confirms `global-feedback-20260907.1`, `en-US`, production API `/`, and unchanged commerce flags.
- Direct public HTML contains all 20 quotes and the translation/edition note without client JavaScript.
- Public browser checks passed at 1440/900/390/320px for three/two/one/one cards, all 20 positions, no Chinese or feedback-section overflow. Real pointer Play advances after 10 seconds and Pause holds for a further 10 seconds.
- Pre-existing whole-page overflow at 900px and 320px is unchanged when the new section is hidden; see the development record. No whole-site responsive fix is claimed.
- Previous LibraryManager English fix checksum remains `81f9ada346cdaf912c3e48216acd7de5493c72b007b258e1ca95ace3fe9e08e0`.

Public screenshots: [desktop](../../design/previews/global-feedback/production/1440.png), [mobile](../../design/previews/global-feedback/production/390.png).

## Baseline and rollback

- Current: `/opt/offersteady-global/releases/20260907-global-feedback-1`.
- Previous: `/opt/offersteady-global/releases/20260907-global-material-english-1`.
- Rollback image: `offersteady-global-web:rollback-before-feedback-20260907`.
- Deployment script: `/tmp/deploy-global-feedback-20260907.sh`.
- Temporary cache-preserving build files: `/tmp/web-global-feedback.Dockerfile` and `/tmp/global-feedback-build-override.yml`; only the final Web build command stamps the new version.
- Source archive SHA256: `b2c0bdf81ba8129a2ba13abc2a97d956670ab42f77b4ec258f8e166f293b420b` (matched on server).

For rollback, retag the saved Web image as latest, recreate only Web from the previous directory with `--no-deps --no-build`, restore the current symlink, then verify health and version. Do not restart core services or delete volumes.
